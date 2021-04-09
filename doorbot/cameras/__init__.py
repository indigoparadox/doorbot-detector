
import logging
import multiprocessing

try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.util import FPSTimer, FrameLock

class Camera( multiprocessing.Process ):

    ''' This should run in the background and keep the stream moving so we
    don't waste time processing old frames. '''

    def __init__( self, **kwargs ):
        super().__init__()

        self.logger = logging.getLogger( 'camera' )

        self.logger.debug( 'setting up camera...' )

        self.width = 0
        self.height = 0
        self.running = True
        self.timer = FPSTimer( self, **kwargs )
        self.daemon = True
        self._frame = FrameLock()
        self._frame_set = False
        self._ready = False
        self._frame_queue = multiprocessing.Queue(
            maxsize=1 )

    @property
    def frame( self ):
        frame_out = None
        while not self._frame_queue.empty():
            frame_out = self._frame_queue.get()
        return frame_out

    @frame.setter
    def frame( self, value ):
        self._frame_queue.put( value.copy() )
        self._ready = True

    @property
    def ready( self ):
        return not self._frame_queue.empty()

    def stop( self ):
        self.running = False
