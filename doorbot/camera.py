
import logging
import threading

try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.util import FPSTimer

class Camera( threading.Thread ):

    ''' This should run in the background and keep the stream moving so we
    don't waste time processing old frames. '''

    def __init__( self, **kwargs ):
        super().__init__()

        logger = logging.getLogger( 'camera.init' )

        logger.debug( 'setting up camera...' )

        self.w = 0
        self.h = 0
        self.running = True
        self.timer = FPSTimer( self, **kwargs )
        self.daemon = True

        self.notifiers = kwargs['notifiers']
        self.capturers = kwargs['capturers']
        self.observer_threads = kwargs['observers']
        self.detector_threads = kwargs['detectors']
        self.overlays = kwargs['overlays']

        self.overlays.start()

        for thd in self.detector_threads:
            thd.cam = self
            thd.start()

        for thd in self.observer_threads:
            thd.cam = self
            thd.start()

    def notify( self, subject, message, snapshot=None ):
        for notifier in self.notifiers:
            notifier.send( subject, message )
        if snapshot:
            for notifier in self.notifiers:
                notifier.snapshot( 'snapshot/{}'.format( subject ), snapshot )

    def process( self, frame ):
        logger = logging.getLogger( 'camera.process' )
        for thd in self.detector_threads:
            logger.debug( 'setting frame for %s...', type( thd ) )
            thd.set_frame( frame )

        for thd in self.observer_threads:
            logger.debug( 'setting frame for %s...', type( thd ) )
            thd.set_frame( frame )

class IPCamera( Camera ):

    def __init__( self, **kwargs ):

        self.attempts = 0
        self.cam_url = kwargs['url']
        self._stream = cv2.VideoCapture( self.cam_url )

        super().__init__( **kwargs )

    def run( self ):

        logger = logging.getLogger( 'camera.ip.run' )

        logger.debug( 'starting camera loop...' )

        while self.running:
            self.timer.loop_timer_start()

            if self._stream.isOpened() and 0 >= self.w:
                self.w = \
                    int( self._stream.get( cv2.CAP_PROP_FRAME_WIDTH ) )
                logger.info( 'video is %d wide', self.w )
            if self._stream.isOpened() and 0 >= self.h:
                self.h = \
                    int( self._stream.get( cv2.CAP_PROP_FRAME_HEIGHT ) )
                logger.info( 'video is %d high', self.h )

            ret, frame = self._stream.read()

            if not ret:
                logger.error( 'camera disconnected!' )
                self._stream.release()
                self.attempts += 1
                logger.info( 'reconnecting (attempt %d)', self.attempts )
                self._stream.open( self.cam_url )
                continue

            self.attempts = 0

            self.process( frame )

            self.timer.loop_timer_end()
