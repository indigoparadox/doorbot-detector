
import logging
import argparse
from configparser import ConfigParser
from threading import Thread

try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.notifiers import MQTTNotifier, LoggerNotifier
from doorbot.capturers import VideoCapture, PhotoCapture
from doorbot.observers import ReserverThread, FramebufferThread
from doorbot.detectors import MotionDetector
from doorbot.cameras import IPCamera
from doorbot.overlays import Overlays, WeatherOverlay
from doorbot.util import FPSTimer

def load_module_config( config, key ):
    out_cfg = {}
    try:
        out_cfg = dict( config.items( key ) )
    except Exception as e:
        logging.error( e )

    if 'enable' in out_cfg and 'true' == out_cfg['enable']:
        return out_cfg

    return None

class Doorbot( Thread ):

    ''' The central glue object of the application. Takes frames from the
    camera and passes them through the detection system. Passes frames of
    interest through the capture system, and then sends notifications. '''

    def __init__( self, config_path, **kwargs ):

        super().__init__()

        self.running = True
        self.timer = FPSTimer( self, **kwargs )
        self.stale_frames = 0

        config = ConfigParser()
        config.read( config_path )

        # Setup the notifier.

        self.notifiers = []

        self.notifiers.append( LoggerNotifier() )

        self.logger = logging.getLogger( 'main' )

        mqtt_cfg = load_module_config( config, 'mqtt' )
        if None != mqtt_cfg:
            self.notifiers.append( MQTTNotifier( **mqtt_cfg ) )

        # Add capturer utilities.

        self.capturers = []

        vcap_cfg = load_module_config( config, 'videocap' )
        if None != vcap_cfg:
            self.capturers.append( VideoCapture( **vcap_cfg ) )

        pcap_cfg = load_module_config( config, 'photocap' )
        if None != pcap_cfg:
            self.capturers.append( PhotoCapture( **pcap_cfg ) )

        # Setup the detector and observer satellite threads.

        self.observer_threads = []

        fb_cfg = load_module_config( config, 'framebuffer' )
        if None != fb_cfg:
            self.observer_threads.append( FramebufferThread( **fb_cfg ) )

        rsrv_cfg = load_module_config( config, 'reserver' )
        if None != rsrv_cfg:
            self.observer_threads.append( ReserverThread( **rsrv_cfg ) )

        # TODO: Make loaded detector configurable.
        self.detector = None
        motion_cfg = load_module_config( config, 'motiondetect' )
        if None != motion_cfg:
            self.detector = MotionDetector( **motion_cfg )

        # TODO: Make loaded overlays configurable.
        self.overlay_thread = Overlays()

        weather_cfg = load_module_config( config, 'weather' )
        if None != weather_cfg:
            self.overlay_thread.overlays.append( WeatherOverlay( **weather_cfg ) )

        cam_cfg = dict( config.items( 'stream' ) )
        self.camera = IPCamera( **cam_cfg )

    def notify( self, subject, message, snapshot=None ):
        for notifier in self.notifiers:
            notifier.send( subject, message )
        if snapshot:
            for notifier in self.notifiers:
                notifier.snapshot( 'snapshot/{}'.format( subject ), snapshot )

    def run( self ):

        ''' Main loop for detection thread. Dispatch relevant messages to other
        threads based on detected activity. '''

        self.logger.debug( 'starting main loop...' )

        self.camera.start()

        self.overlay_thread.start()

        #for thd in self.detector_threads:
        #    thd.cam = self
        #    thd.start()

        for thd in self.observer_threads:
            thd.cam = self
            thd.start()

        while self.running:
            self.timer.loop_timer_start()

            # Spin until we have a new frame to process.
            if not self.camera.ready:
                logger.debug( 'waiting for frame...' )
                self.timer.loop_timer_end()
                continue
            elif self.camera.frame_stale:
                self.stale_frames += 1
                self.timer.loop_timer_end()
                continue

            #logger.debug( 'processing frame...' )
            if self.stale_frames:
                self.logger.debug( 'skipped %d stale frames', self.stale_frames )
                self.stale_frames = 0
            
            # The camera provides a copy while using the proper locks.
            frame = self.camera.frame

            #if not frame:
            #    self.timer.loop_timer_end()
            #    continue

            # TODO: Move into its own overlay module.
            if 'motion' not in self.overlay_thread.highlights:
                self.overlay_thread.highlights['motion'] = {'boxes': []}
            self.overlay_thread.highlights['motion']['boxes'] = []

            event = self.detector.detect( frame )
            if event and 'movement' == event.event_type:
                for capturer in self.capturers:
                    capturer.handle_motion_frame( frame, self.camera.width, self.camera.height )

                # TODO: Send notifier w/ summary of current objects.
                # TODO: Make this summary retained.
                # TODO: Send image data.
                ret, jpg = cv2.imencode( '.jpg', event.frame )
                self.notify( 'movement', '{} at {}'.format(
                    event.dimensions, event.position ), snapshot=jpg.tostring() )

                # TODO: Vary color based on type of object.
                color = (255, 0, 0)
                self.overlay_thread.highlights['motion']['boxes'].append( {
                    'x1': event.position[0], 'y1': event.position[1],
                    'x2': event.position[0] + event.dimensions[0],
                    'y2': event.position[1] + event.dimensions[1],
                    'color': color
                } )
            else:
                # No motion frames were found, digest capture pipeline.
                for capturer in self.capturers:
                    capturer.finalize_motion( frame, self.camera.width, self.camera.height )

            self.timer.loop_timer_end()

def main():

    global logger

    parser = argparse.ArgumentParser()

    verbosity_grp = parser.add_mutually_exclusive_group()

    verbosity_grp.add_argument( '-v', '--verbose', action='store_true' )

    verbosity_grp.add_argument( '-q', '--quiet', action='store_true' )

    parser.add_argument(
        '-c', '--config', action='store', default='detector.ini' )

    #parser.add_argument(
    #    '-f', '--fps', action='store', type=float, default=5.0,
    #    help='FPS to run main loop at. Does NOT affect camera FPS.' )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig( level=logging.DEBUG )
        logging.getLogger( 'doorbot.run' ).setLevel( logging.INFO )
        logging.getLogger( 'doorbot.process' ).setLevel( logging.WARNING )
        logging.getLogger( 'camera.process' ).setLevel( logging.WARNING )
        logging.getLogger( 'framelock' ).setLevel( logging.ERROR )
    elif args.quiet:
        logging.basicConfig( level=logging.ERROR )
    else:
        logging.basicConfig( level=logging.INFO )
        logging.getLogger( 'framelock' ).setLevel( logging.ERROR )
    logger = logging.getLogger( 'main' )

    app = Doorbot( args.config )

    app.start()
    app.join()

if '__main__' == __name__:
    try:
        main()
    except KeyboardInterrupt as e:
        logger.info( 'quitting on ctrl-c' )
