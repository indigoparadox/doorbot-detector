
from threading import Thread
import logging
import cv2

class Camera( Thread ):

    ''' This should run in the background and keep the stream moving so we
    don't waste time processing old frames. '''

    def __init__( self, url ):
        super().__init__()
        
        logger = logging.getLogger( 'camera.init' )

        logger.debug( 'setting up camera...' )

        self.daemon = True
        self.running = True
        self._ret = False
        self._frame = None
        self._stream = cv2.VideoCapture( url )
        
    def run( self ):
        
        logger = logging.getLogger( 'camera.run' )
        
        logger.debug( 'starting camera loop...' )

        while self.running:
            # No lock needed here because this thread will be the only one
            # to set this frame.
            self._ret, self._frame = self._stream.read()

    def frame( self ):
        try:
            return self._ret, self._frame.copy()
        except:
            return False, None

