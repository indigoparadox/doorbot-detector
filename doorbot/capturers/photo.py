
import logging
import os
from threading import Thread
from datetime import datetime

try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.capturers import Capture

class PhotoCapture( Capture ):

    class PhotoCaptureWriter( Thread ):

        def __init__( self, path, timestamp, frame ):
            super().__init__()

            logger = logging.getLogger('capture.photo.writer.init' )

            logger.info( 'creating photo writer for %s.jpg...',
                os.path.join( path, timestamp ) )

            self.path = path
            self.timestamp = timestamp
            self.frame = frame
            self.daemon = True

        def run( self ):
            logger = logging.getLogger( 'capture.photo.writer.run' )

            filename = '{}/{}.mp4'.format( self.path, self.timestamp )

            logger.info( 'writing %s...', filename )

            cv2.imwrite( filename, self.frame )

            logger.info( 'writing %s complete', filename )

    def handle_motion_frame( self, frame, width, height ):

        # Individually process the last snapshot.
        timestamp = datetime.now().strftime( self.ts_format )
        encoder = self.PhotoCaptureWriter( self.path, timestamp, frame.copy() )
        encoder.start()

    def finalize_motion( self, frame, width, height ):

        ''' Dummy override. Frames are handled individually in
        handle_motion_frame(). '''

PLUGIN_TYPE = 'capturers'
PLUGIN_CLASS = PhotoCapture
