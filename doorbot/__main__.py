
import logging
import argparse
from configparser import RawConfigParser
from threading import Thread

from doorbot.portability import image_to_jpeg, is_frame
from doorbot.overlays.opencv import OpenCVOverlays
from doorbot.util import FPSTimer, load_modules

class Doorbot( Thread ):

    ''' The central glue object of the application. Takes frames from the
    camera and passes them through the detection system. Passes frames of
    interest through the capture system, and then sends notifications. '''

    def __init__( self, config_path, **kwargs ):

        super().__init__()

        self.running = True
        self.timer = FPSTimer( self, **kwargs )
        self.stale_frames = 0

        config = RawConfigParser()
        config.read( config_path )
        module_configs = load_modules( config )

        self.logger = logging.getLogger( 'main' )

        # Setup the notifier.

        self.notifiers = []

        for notifier_cfg in module_configs['notifiers']:
            notifier = notifier_cfg['module'].PLUGIN_CLASS( **notifier_cfg )
            self.notifiers.append( notifier )

        # Add capturer utilities.

        self.capturers = []

        for capturer_cfg in module_configs['capturers']:
            capturer = capturer_cfg['module'].PLUGIN_CLASS( **capturer_cfg )
            self.capturers.append( capturer )

        # Setup the detector and observer satellite threads.

        self.observer_procs= []

        for observer_cfg in module_configs['observers']:
            observer = observer_cfg['module'].PLUGIN_CLASS( **observer_cfg )
            self.observer_procs.append( observer )

        self.detectors = []

        for detector_cfg in module_configs['detectors']:
            detector = detector_cfg['module'].PLUGIN_CLASS( **detector_cfg )
            self.detectors.append( detector )

        self.overlay_thread = OpenCVOverlays()

        for overlay_cfg in module_configs['overlays']:
            overlay = overlay_cfg['module'].PLUGIN_CLASS( **overlay_cfg )
            self.overlay_thread.add_overlay( overlay )

        self.camera = \
            module_configs['cameras'][0]['module'].PLUGIN_CLASS(
                **module_configs['cameras'][0] )

    def notify( self, subject, message, has_frame, frame=None ):
        for notifier in self.notifiers:
            notifier.send( subject, message )
        if has_frame:
            for notifier in self.notifiers:
                overlayed_frame = frame.copy()
                overlayed_frame = self.overlay_thread.draw( overlayed_frame, **notifier.kwargs )
                jpg = image_to_jpeg( overlayed_frame )
                notifier.snapshot( 'snapshot/{}'.format( subject ), jpg )

    def capture( self, frame ):
        for capturer in self.capturers:
            if is_frame( frame ):
                overlayed_frame = frame.copy()
                overlayed_frame = \
                    self.overlay_thread.draw(
                        overlayed_frame, **capturer.kwargs )
                capturer.handle_motion_frame( overlayed_frame )
            else:
                # We get passed "None" if we just want to update capturer
                # grace frames, etc.
                capturer.handle_motion_frame( None )

    def run( self ):

        ''' Main loop for detection thread. Dispatch relevant messages to other
        threads based on detected activity. '''

        self.logger.debug( 'starting main loop...' )

        self.camera.start()

        self.overlay_thread.start()

        for proc in self.observer_procs:
            proc.start()

        frame = None
        overlayed_frame = None
        event = None

        while self.running:
            self.timer.loop_timer_start()

            # Spin until we have a new frame to process.
            if not self.camera.ready:
                self.logger.debug( 'waiting for frame...' )
                self.timer.loop_timer_end()
                continue
            elif self.camera.frame_stale:
                self.stale_frames += 1
                self.timer.loop_timer_end()
                continue

            #logger.debug( 'processing frame...' )
            if self.stale_frames:
                #self.logger.debug( 'skipped %d stale frames', self.stale_frames )
                self.stale_frames = 0

            # The camera provides a copy while using the proper locks.
            frame = self.camera.frame

            for observer in self.observer_procs:
                overlayed_frame = frame.copy()
                overlayed_frame = self.overlay_thread.draw(
                    overlayed_frame, **observer.kwargs )
                observer.set_frame( overlayed_frame )

            event = self.detectors[0].detect( frame )
            if event and 'movement' == event.event_type:
                self.capture( frame )
                self.notify( 'movement', '{} at {}'.format(
                    event.dimensions, event.position ), True, frame=frame )
            else:
                # No motion frames were found, digest capture pipeline.
                self.capture( None )

            self.timer.loop_timer_end()

def main():

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
        #logging.getLogger( 'doorbot.run' ).setLevel( logging.INFO )
        #logging.getLogger( 'doorbot.process' ).setLevel( logging.WARNING )
        #logging.getLogger( 'camera.process' ).setLevel( logging.WARNING )
        logging.getLogger( 'framelock' ).setLevel( logging.ERROR )
    elif args.quiet:
        logging.basicConfig( level=logging.ERROR )
    else:
        logging.basicConfig( level=logging.INFO )
        logging.getLogger( 'framelock' ).setLevel( logging.ERROR )
    #logger = logging.getLogger( 'main' )

    app = Doorbot( args.config )

    app.start()
    app.join()

if '__main__' == __name__:
    #try:
    main()
    #except KeyboardInterrupt as e:
    #    logger.info( 'quitting on ctrl-c' )
