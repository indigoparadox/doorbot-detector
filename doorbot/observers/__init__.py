
import logging
import multiprocessing
import threading
from queue import Full
from contextlib import contextmanager

try:
    from cv2 import cv2
except ImportError:
    import cv2

from ..util import FPSTimer, FrameLock

class ObserverProc( multiprocessing.Process ):

    def __init__( self, **kwargs ):
        super().__init__()
        self.daemon = True
        self._frame = FrameLock()
        self.timer = FPSTimer( self, **kwargs )
        self._running = True
        self._frame_update_thread : threading.Thread
        self.logger = logging.getLogger( 'observer' )
        self._frame_queue = multiprocessing.Queue(
            maxsize=int( kwargs['queuesize'] ) \
                if 'queuesize' in kwargs else 20 )
        self.camera_key = kwargs['camera']

        # These are only defined for the subprocess, as they are only usable
        # on the other side of the queue.
        self.get_frame = None
        self.frame_ready = None

        # Save these to pass to overlays, later.
        self.kwargs = kwargs

    @property
    def running( self ):
        return self._running

    def set_frame( self, value ):
        #self._frame.set_frame( value )
        try:
            self._frame_queue.put_nowait( value )
        except Full:
            self.logger.warning( 'queue full; skipping...' )

    def loop( self ):

        ''' This should be overridden by each observer with the contents of its
        actual run() thread. The real run() is used below to setup the frame
        transport. '''

    def run( self ):

        def frame_update():
            while self._running:
                frame = None
                found_frame = False
                while not self._frame_queue.empty():
                    frame = self._frame_queue.get()
                    found_frame = True
                if found_frame:
                    self._frame.set_frame( frame )

        # These handlers are needed to "wrap" camera inside process.
        self.get_frame = lambda: self._frame.get_frame() #pylint: disable=unnecessary-lambda
        self.frame_ready = lambda: self._frame.frame_ready

        self._frame_update_thread = threading.Thread( target=frame_update, daemon=True )
        self._frame_update_thread.start()

        try:
            self.loop()
        except Exception as exc: #pylint: disable=broad-except
            self.logger.exception( exc )

    def stop( self ):
        self._running = False
