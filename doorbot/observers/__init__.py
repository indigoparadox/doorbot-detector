
import logging
import threading
from contextlib import contextmanager

try:
    from cv2 import cv2
except ImportError:
    import cv2

from ..util import FPSTimer, FrameLock

class ObserverThread( threading.Thread ):

    def set_frame( self, value ):
        self._frame.set_frame( value )

    def __init__( self, **kwargs ):
        super().__init__()
        self.daemon = True
        self._frame = FrameLock()
        self.timer = FPSTimer( self, **kwargs )
        self.running = True
        self.logger = logging.getLogger( 'observer' )

        # Save these to pass to overlays, later.
        self.kwargs = kwargs
