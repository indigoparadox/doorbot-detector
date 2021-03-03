
import logging
import os

import numpy
try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.capturers import Capture, CaptureWriter

class PhotoCaptureWriter( CaptureWriter ):

    def __init__( self, timestamp, width, height, **kwargs ):
        super().__init__( timestamp, width, height, **kwargs )

        self.logger = logging.getLogger('capture.photo' )

        self.logger.info( 'creating photo writer for %s.jpg...',
            os.path.join( self.path, self.timestamp ) )

    def start( self ):

        filename = '{}/{}.jpg'.format( self.path, self.timestamp )

        self.logger.info( 'writing %s...', filename )

        assert( 1 == len( self.frame_array ) )
        cv2.imwrite( filename, self.frame_array[0] )

        self.logger.info( 'writing %s complete', filename )

class PhotoCapture( Capture ):

    def __init__( self, **kwargs ):
        super().__init__( numpy.ndarray, **kwargs )

    def handle_motion_frame( self, frame : numpy.ndarray ):

        # Individually process the last snapshot.
        super().create_or_append_to_writer( frame, PhotoCaptureWriter )
        self.writer.start()
        self.writer = None

    def finalize_motion( self, frame : numpy.ndarray ):

        pass

PLUGIN_TYPE = 'capturers'
PLUGIN_CLASS = PhotoCapture
