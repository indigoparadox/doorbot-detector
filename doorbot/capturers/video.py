
import os
import logging
from tempfile import TemporaryDirectory

import numpy

try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.portability import is_frame
from doorbot.capturers import Capture, CaptureWriter

class VideoCaptureWriter( CaptureWriter ):
    def __init__( self, camera_key, timestamp, width, height, **kwargs ):
        super().__init__( camera_key, timestamp, width, height, **kwargs )

        self.logger = logging.getLogger('capture.video.{}'.format( camera_key ) )

        self.fps = float( kwargs['fps'] ) if 'fps' in kwargs else 15.0
        self.fourcc = kwargs['fourcc'] if 'fourcc' in kwargs else 'mp4v'
        self.container = kwargs['container'] if 'container' in kwargs else 'mp4'

        self.logger.debug( 'creating video writer for %s.mp4...',
            os.path.join( self.path, self.timestamp ) )

    def start( self ):

        # This will run in its own process. The queue is used to pass frames
        # in.

        temp_dir = TemporaryDirectory()

        # Determine path for saved video/temporary video.
        filename = '{}.{}'.format( self.timestamp, self.container )
        filepath = filename
        if self.path.startswith( 'ftp:' ) or self.path.startswith( 'ftps:' ):
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
        if self.path.startswith( 'ftp:' ) or self.path.startswith( 'ftps:' ):
            self.upload_ftp_or_backup( filepath, filename, temp_dir )

        self.logger.info( 'encoding %s completed', filename )

class VideoCapture( Capture ):

    def __init__( self, **kwargs ):
        super().__init__( numpy.ndarray, **kwargs )

        self.logger = logging.getLogger( 'capture.video.{}'.format( self.camera_key) )
        self.logger.info( 'setting up video capture...' )

        self.max_frames = int( kwargs['maxframes'] ) \
            if 'maxframes' in kwargs else 100
        self.frames_count = 0

        self.grace_frames = int( kwargs['graceframes'] ) \
            if 'graceframes' in kwargs else 10
        self.grace_remaining = 0

    def create_or_append_to_writer( self, frame ):
        if None == self.writer:
            self.grace_remaining = self.grace_frames
        else:
            self.grace_remaining -= 1
        super().create_or_append_to_writer( frame, VideoCaptureWriter )
        self.frames_count += 1

    def handle_motion_frame( self, frame : numpy.ndarray ):

        if self.frames_count >= self.max_frames:
            # Finalize motion to break up video into chunks.
            self.grace_remaining = 0
            self.finalize_motion( frame )
        elif is_frame( frame ):
            self.create_or_append_to_writer( frame.copy() )
        else:
            self.finalize_motion( frame )

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
