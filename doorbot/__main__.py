
import sys
import argparse
import logging
from logging.handlers import SMTPHandler
from configparser import NoOptionError, NoSectionError
#from threading import Thread
from urllib.parse import urlparse

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

        self.notifiers = []

        for notifier_cfg in config['notifiers']:
            notifier = notifier_cfg['module'].PLUGIN_CLASS( **notifier_cfg )
            self.notifiers.append( notifier )

        # Add capturer utilities.

        self.capturers = []

        for capturer_cfg in config['capturers']:
            capturer = capturer_cfg['module'].PLUGIN_CLASS( **capturer_cfg )
            self.capturers.append( capturer )

        # Setup the detector and observer satellite threads.

        self.observer_procs= []

        for observer_cfg in config['observers']:
            observer = observer_cfg['module'].PLUGIN_CLASS( **observer_cfg )
            self.observer_procs.append( observer )

        self.detectors = []

        for detector_cfg in config['detectors']:
            detector = detector_cfg['module'].PLUGIN_CLASS( **detector_cfg )
            self.detectors.append( detector )

        self.overlay_thread = OpenCVOverlays()

        for overlay_cfg in config['overlays']:
            overlay = overlay_cfg['module'].PLUGIN_CLASS( **overlay_cfg )
            self.overlay_thread.add_overlay( overlay )

        #try:
        self.camera = \
            config['cameras'][0]['module'].PLUGIN_CLASS(
                **config['cameras'][0] )
        #except:
        #    self.logger.error( 'at least one camera must be configured!' )
        #    sys.exit( 1 )

    def notify( self, subject, message, has_frame, frame=None ):
        for notifier in self.notifiers:
            notifier.send( subject, message )
        if has_frame:
            for notifier in self.notifiers:
                overlayed_frame = frame.copy()
                overlayed_frame = self.overlay_thread.draw( overlayed_frame, **notifier.kwargs )
                jpg = image_to_jpeg( overlayed_frame )
                notifier.snapshot( subject, jpg )

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
                #self.logger.debug( 'waiting for frame...' )
                self.timer.loop_timer_end()
                continue
            #elif self.camera.frame_stale:
            #    self.stale_frames += 1
            #    self.timer.loop_timer_end()
            #    continue

            #logger.debug( 'processing frame...' )
            #if self.stale_frames:
            #    #self.logger.debug( 'skipped %d stale frames', self.stale_frames )
            #    self.stale_frames = 0

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

    except (NoOptionError, NoSectionError) as exc:
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
            app.camera.stop()
            app.overlay_thread.stop()
            for proc in app.observer_procs:
                proc.stop()
        sys.exit( 0 )

    except Exception as exc: # pylint: disable=broad-except
        logger.error( '%s: %s', type( exc ), exc )

if '__main__' == __name__:
    main()
