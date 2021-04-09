
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

        self.logger = logging.getLogger( 'camera' )

        self.logger.debug( 'setting up camera...' )

        self.width = 0
        self.height = 0
        self.running = True
        self.timer = FPSTimer( self, **kwargs )
        self.daemon = True
        self._frame = FrameLock()
        self.frame_stale = False
        self._frame_set = False
        self._ready = False

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

    def stop( self ):
        self.running = False
