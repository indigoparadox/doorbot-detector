
import logging
import threading

try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.util import FPSTimer, FrameLock

class Camera( threading.Thread ):

    ''' This should run in the background and keep the stream moving so we
    don't waste time processing old frames. '''

    def __init__( self, **kwargs ):
        super().__init__()

        logger = logging.getLogger( 'camera.init' )

        logger.debug( 'setting up camera...' )

        self.width = 0
        self.height = 0
        self.running = True
        self.timer = FPSTimer( self, **kwargs )
        self.daemon = True
        self._frame = FrameLock()
        self.frame_stale = False
        self._frame_set = False
        self._ready = False

        '''
        self.notifiers = kwargs['notifiers']
        self.capturers = kwargs['capturers']
        self.observer_threads = kwargs['observers']
        self.detector_threads = kwargs['detectors']
        self.overlays = kwargs['overlays']
        '''

    @property
    def frame( self ):
        frame_out = None
        if self._ready:
            with self._frame.get_frame() as frame:
                frame_out = frame.copy()
                self.frame_stale = True
        return frame_out

    @frame.setter
    def frame( self, value ):
        self._frame.set_frame( value )
        self.frame_stale = False
        self._ready = True

    @property
    def ready( self ):
        return self._ready

class IPCamera( Camera ):

    def __init__( self, **kwargs ):

        self.attempts = 0
        self.cam_url = kwargs['url']
        self._stream = cv2.VideoCapture( self.cam_url )
        self.logger = logging.getLogger( 'camera' )

        super().__init__( **kwargs )

    def run( self ):

        self.logger.debug( 'starting camera loop...' )

        while self.running:
            self.timer.loop_timer_start()

            if self._stream.isOpened() and 0 >= self.width:
                self.width = \
                    int( self._stream.get( cv2.CAP_PROP_FRAME_WIDTH ) )
                self.logger.info( 'video is %d wide', self.width )
            if self._stream.isOpened() and 0 >= self.height:
                self.height = \
                    int( self._stream.get( cv2.CAP_PROP_FRAME_HEIGHT ) )
                self.logger.info( 'video is %d high', self.height )

            ret, frame = self._stream.read()

            if not ret:
                self.logger.error( 'camera disconnected!' )
                self._stream.release()
                self.attempts += 1
                self.logger.info( 'reconnecting (attempt %d)', self.attempts )
                self._stream.open( self.cam_url )
                self.timer.loop_timer_end()
                continue

            self.attempts = 0

            self.frame = frame

            #self.process( frame )

            self.timer.loop_timer_end()
