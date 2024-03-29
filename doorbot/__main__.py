
import sys
import argparse
import logging
from logging.handlers import SMTPHandler
from configparser import NoOptionError, NoSectionError
#from threading import Thread
from urllib.parse import urlparse
from threading import Thread

from doorbot.portability import image_to_jpeg, is_frame
from doorbot.overlays.opencv import OpenCVOverlays
from doorbot.util import FPSTimer
from doorbot.config import DoorbotConfig

class Doorbot( object ):

    ''' The central glue object of the application. Takes frames from the
    camera and passes them through the detection system. Passes frames of
    interest through the capture system, and then sends notifications. '''

    def __init__( self, config : DoorbotConfig, **kwargs ):

        super().__init__()

        self.running = True
        self.timer = FPSTimer( self, **kwargs )
        #self.stale_frames = 0

        self.logger = logging.getLogger( 'main' )

        # Setup the notifier.

        self.notifiers = {}

        for notifier_key in config['notifiers']:
            notifier_cfg = config['notifiers'][notifier_key]
            notifier = notifier_cfg['module'].PLUGIN_CLASS( notifier_key, **notifier_cfg )
            self.notifiers[notifier_key] = notifier

        # Add capturer utilities.

        self.capturers = {}

        for capturer_key in config['capturers']:
            capturer_cfg = config['capturers'][capturer_key]
            capturer = capturer_cfg['module'].PLUGIN_CLASS( capturer_key, **capturer_cfg )
            self.capturers[capturer_key] = capturer

        # Setup the detector and observer satellite threads.

        self.observer_procs= {}

        for observer_key in config['observers']:
            observer_cfg = config['observers'][observer_key]
            observer = observer_cfg['module'].PLUGIN_CLASS( observer_key, **observer_cfg )
            self.observer_procs[observer_key] = observer

        self.detectors = {}

        for detector_key in config['detectors']:
            detector_cfg = config['detectors'][detector_key]
            detector = detector_cfg['module'].PLUGIN_CLASS( detector_key, **detector_cfg )
            self.detectors[detector_key] = detector

        self.overlay_thread = OpenCVOverlays()

        for overlay_key in config['overlays']:
            overlay_cfg = config['overlays'][overlay_key]
            overlay = overlay_cfg['module'].PLUGIN_CLASS( overlay_key, **overlay_cfg )
            self.overlay_thread.add_overlay( overlay_key, overlay )

        self.cameras = {}
        for camera_key in config['cameras']:
            camera_cfg = config['cameras'][camera_key]
            self.logger.debug( 'setting up camera with plugin: %s', camera_cfg['module'] )
            camera = camera_cfg['module'].PLUGIN_CLASS( camera_key, **camera_cfg )
            self.cameras[camera_key] = camera

    def notify( self, camera_key, subject, message, has_frame, frame=None ):

        for notifier_key in self.notifiers:
            # TODO: Limit to instances.
            notifier = self.notifiers[notifier_key]
            if notifier.camera_key != camera_key:
                continue
            notifier.send( subject, message )

        if not has_frame:
            return

        for notifier_key in self.notifiers:
            # TODO: Limit to instances.
            notifier = self.notifiers[notifier_key]
            if notifier.camera_key != camera_key:
                continue
            overlayed_frame = frame.copy()
            overlayed_frame = self.overlay_thread.draw( camera_key, overlayed_frame, **notifier.kwargs )
            jpg = image_to_jpeg( overlayed_frame )
            notifier.snapshot( subject, jpg )

    def capture( self, camera_key, frame ):
        for capturer_key in self.capturers:
            # TODO: Limit to instances.
            capturer = self.capturers[capturer_key]
            if capturer.camera_key != camera_key:
                continue
            if is_frame( frame ):
                overlayed_frame = frame.copy()
                overlayed_frame = \
                    self.overlay_thread.draw(
                        camera_key, overlayed_frame, **capturer.kwargs )
                capturer.handle_motion_frame( overlayed_frame )
            else:
                # We get passed "None" if we just want to update capturer
                # grace frames, etc.
                capturer.handle_motion_frame( None )

    def run_camera( self, camera_key ):
        camera = self.cameras[camera_key]

        self.timer.loop_timer_start()

        # Spin until we have a new frame to process.
        if not camera.ready:
            #self.logger.debug( 'waiting for frame...' )
            self.timer.loop_timer_end()
            return

        # The camera provides a copy while using the proper locks.
        frame = camera.frame

        for observer_key in self.observer_procs:
            # TODO: Limit to instances.
            observer = self.observer_procs[observer_key]
            if observer.camera_key != camera_key:
                continue
            overlayed_frame = frame.copy()
            overlayed_frame = self.overlay_thread.draw(
                camera_key, overlayed_frame, **observer.kwargs )
            observer.set_frame( overlayed_frame )

        for detector_key in self.detectors:
            # TODO: Limit to instances.
            detector = self.detectors[detector_key]
            event = detector.detect( frame )
            if detector.camera_key != camera_key:
                continue
            if event and 'movement' == event.event_type:
                self.capture( camera_key, frame )
                self.notify( camera_key, 'movement', '{} at {}'.format(
                    event.dimensions, event.position ), True, frame=frame )
            else:
                # No motion frames were found, digest capture pipeline.
                self.capture( camera_key, None )

        self.timer.loop_timer_end()

    def run( self ):

        ''' Main loop for detection thread. Dispatch relevant messages to other
        threads based on detected activity. '''

        self.logger.debug( 'starting main loop...' )

        for camera_key in self.cameras:
            self.cameras[camera_key].start()

        self.overlay_thread.start()

        for observer_key in self.observer_procs:
            proc = self.observer_procs[observer_key]
            proc.start()

        while self.running:
            for camera_key in self.cameras:
                self.run_camera( camera_key )

def main():

    parser = argparse.ArgumentParser(
        'doorbot', description='camera monitoring and activity detection' )

    verbosity_grp = parser.add_mutually_exclusive_group()

    verbosity_grp.add_argument(
        '-v', '--verbose', action='store_true',
        help='show debug messages on stdout' )

    verbosity_grp.add_argument(
        '-m', '--metric', action='store_true',
        help='show fps counts every so often on stdout' )

    verbosity_grp.add_argument(
        '-q', '--quiet', action='store_true',
        help='be as silent as possible on stdout' )

    parser.add_argument(
        '-c', '--config', action='store', default=None,
        help='manually specify a location for the config file to use' )

    parser.add_argument(
        '-o', '--option', action='append', nargs=3,
        metavar=('section', 'option', 'value'),
        help='specify a manual override for the given option' )

    parser.add_argument(
        '-f', '--fps', action='store', default=10.0,
        help='master loop FPS' )

    args = parser.parse_args()

    if not args.option:
        args.option = []

    config = DoorbotConfig( args.config, args.option )

    if args.verbose:
        logging.basicConfig( level=logging.DEBUG )
        #logging.getLogger( 'doorbot.run' ).setLevel( logging.INFO )
        #logging.getLogger( 'doorbot.process' ).setLevel( logging.WARNING )
        #logging.getLogger( 'camera.process' ).setLevel( logging.WARNING )
        logging.getLogger( 'urllib3.connectionpool' ).setLevel( logging.WARNING )
        logging.getLogger( 'fps.timer' ).setLevel( logging.WARNING )
        logging.getLogger( 'framelock' ).setLevel( logging.ERROR )
    elif args.quiet:
        logging.basicConfig( level=logging.ERROR )
    else:
        logging.basicConfig( level=logging.INFO )
        logging.getLogger( 'framelock' ).setLevel( logging.ERROR )
        logging.getLogger( 'fps.timer' ).setLevel( logging.ERROR )
    logger = logging.getLogger( 'main' )

    if args.metric:
        logging.getLogger( 'fps.timer' ).setLevel( logging.DEBUG )

    try:
        smtp_server = urlparse( config.parser['exceptions']['smtpserver'] )
        smtp_handler = SMTPHandler(
            (smtp_server.hostname,
                smtp_server.port if smtp_server.port else 25),
            config.parser['exceptions']['smtpfrom'],
            config.parser['exceptions']['smtpto'].split( ',' ),
            '[doorbot] Exception Occurred' )
        if smtp_server.username:
            smtp_handler.username = smtp_server.username
        if smtp_server.password:
            smtp_handler.password = smtp_server.password
        if 'smtps' == smtp_server.scheme:
            smtp_handler.secure = ()
        smtp_handler.setLevel( logging.ERROR )
        logging.getLogger( '' ).addHandler( smtp_handler )
        logger.info( 'exception reporter initialized' )

    except (NoOptionError, NoSectionError, KeyError) as exc:
        logger.info( 'could not setup exception reporter: %s', exc )

    #app.start()
    #app.join()
    app = None
    try:
        app = Doorbot( config, fps=args.fps )

        app.run()
    except KeyboardInterrupt:
        logger.info( 'quitting on ctrl-c' )
        if app:
            for camera_key in app.cameras:
                app.cameras[camera_key].stop()
            app.overlay_thread.stop()
            for observer_key in app.observer_procs:
                app.observer_procs[observer_key].stop()
        sys.exit( 0 )

    except Exception as exc: # pylint: disable=broad-except
        logger.exception( exc )

if '__main__' == __name__:
    main()
