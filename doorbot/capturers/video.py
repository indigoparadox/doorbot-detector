
import os
import logging
from tempfile import TemporaryDirectory

import numpy

try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.capturers import Capture, CaptureWriter, CaptureWriterProcess

class VideoLengthException( Exception ):
    pass

class VideoCaptureWriter( CaptureWriter ):
    def __init__( self, timestamp, width, height, **kwargs ):
        super().__init__( timestamp, width, height, **kwargs )

        self.logger = logging.getLogger('capture.video' )

        self.logger.debug( 'creating video writer for %s.mp4...',
            os.path.join( self.path, self.timestamp ) )

    def start( self ):

        # This will run in its own process. The queue is used to pass frames
        # in.

        temp_dir = TemporaryDirectory()

        # Determine path for saved video/temporary video.
        filename = '{}.{}'.format( self.timestamp, self.container )
        filepath = filename
        if self.path.startswith( 'ftp:' ):
            filepath = os.path.join( temp_dir.name, filename )
        else:
            filepath = os.path.join( self.path, filename )

        self.logger.info( 'encoding %s (%d frames, %d fps)...',
            filepath, len( self.frame_array ), self.fps )

        # Encode the video file.
        fourcc = cv2.VideoWriter_fourcc( *(self.fourcc) )
        encoder = \
            cv2.VideoWriter(
                filepath, fourcc, self.fps, (self.width, self.height) )
        while 0 < len( self.frame_array ):
            frame = self.frame_array.pop()
            self.logger.debug( 'writing frame %dx%d to video %dx%d...',
                frame.shape[1], frame.shape[0], self.width, self.height )
            assert( self.width == frame.shape[1] )
            assert( self.height == frame.shape[0] )
            encoder.write( frame )
        encoder.release()

        # Try to upload file if remote path specified.
        if self.path.startswith( 'ftp:' ):
            self.upload_ftp_or_backup( filepath, filename, temp_dir )

        self.logger.info( 'encoding %s completed', filename )

class VideoCapture( Capture ):

    def __init__( self, **kwargs ):
        super().__init__( numpy.ndarray, **kwargs )

        self.logger = logging.getLogger( 'capture.video' )
        self.logger.info( 'setting up video capture...' )

        self.max_frames = int( kwargs['maxframes'] ) \
            if 'maxframes' in kwargs else 100
        self.frames_count = 0

    def create_or_append_to_writer( self, frame ):
        super().create_or_append_to_writer( frame, VideoCaptureWriter )
        self.frames_count += 1

    def handle_motion_frame( self, frame : numpy.ndarray ):

        if self.frames_count >= self.max_frames:
            # Have the caller finalize with this frame instead to break the
            # video up into chunks.
            raise VideoLengthException(
                'motion exceeded maximum {} frames'.format(
                self.max_frames ) )
        else:
            self.create_or_append_to_writer( frame.copy() )

    def finalize_motion( self, frame : numpy.ndarray ):
        if None == self.writer and isinstance( frame, numpy.ndarray ):
            self.create_or_append_to_writer( frame.copy() )

        # Ship the frames off to a separate thread to write out.
        if 0 < self.frames_count:
            self.frames_count = 0
            self.writer.start()
            self.writer = None

PLUGIN_TYPE = 'capturers'
PLUGIN_CLASS = VideoCapture
