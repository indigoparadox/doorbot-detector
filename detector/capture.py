
import cv2
import logging
import os
from datetime import datetime
from threading import Thread

class Capture( object ):

    def __init__( self, **kwargs ):

        self.path = kwargs['path'] if 'path' in kwargs else '/tmp'
        self.ts_format = kwargs['tsformat'] if 'tsformat' in kwargs else \
            '%Y-%m-%d-%H-%M-%S-%f'

    def start_motion( self, frame ):
        pass

    def process_motion( self, frame ):
        pass

class VideoCapture( Capture ):

    class VideoCaptureWriter( Thread ):
        def __init__( self, path, w, h, fps, timestamp, fourcc, container ):
            super().__init__()

            logger = logging.getLogger('capture.video.writer.init' )

            logger.info( 'creating video writer for {}.mp4...'.format(
                os.path.join( path, timestamp ) ) )

            self.path = path
            self.timestamp = timestamp
            self.frames = []
            self.w = w
            self.h = h
            self.fps = fps
            self.fourcc = fourcc
            self.container = container
            self.daemon = True

        def run( self ):

            logger = logging.getLogger( 'capture.video.writer.run' )

            filename = '{}/{}.{}'.format( self.path, self.timestamp,
                self.container )

            logger.info( 'encoding {} ({} frames, {} fps)...'.format(
                filename, len( self.frames ), self.fps ) )

            fourcc = cv2.VideoWriter_fourcc( *(self.fourcc) )
            encoder = \
                cv2.VideoWriter( filename, fourcc, self.fps, (self.w, self.h) )
            for frame in self.frames:
                encoder.write( frame )
            encoder.release()

            logger.info( 'encoding {} completed'.format( filename ) )

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )

        logger = logging.getLogger( 'capture.video.init' )
        logger.info( 'setting up video capture...' )

        self.grace_remaining = 0

        self.grace_frames = int( kwargs['graceframes'] ) \
            if 'graceframes' in kwargs else 0
        self.fps = float( kwargs['fps'] ) if 'fps' in kwargs else 15.0
        self.fourcc = kwargs['fourcc'] if 'fourcc' in kwargs else 'mp4v'
        self.container = kwargs['container'] if 'container' in kwargs else 'mp4'

        self.encoder = None

    def _create_or_append_to_encoder( self, frame, w, h ):
        if None == self.encoder:
            timestamp = datetime.now().strftime( self.ts_format )
            self.encoder = self.VideoCaptureWriter(
                self.path, w, h, self.fps, timestamp, self.fourcc,
                self.container )

        self.encoder.frames.append( frame )

    def append_motion( self, frame, w, h ):

        self._create_or_append_to_encoder( frame.copy(), w, h )

        # Start/reset grace countdown.
        self.grace_remaining = self.grace_frames

    def process_motion( self, frame, w, h ):
        if 0 < self.grace_remaining and None != self.encoder:
            # Append grace frame.
            self._create_or_append_to_encoder( frame.copy(), w, h )
            self.grace_remaining -= 1

        elif None != self.encoder:
            # Ship the frames off to a separate thread to write out.
            self.encoder.start()
            self.encoder = None

class PhotoCapture( Capture ):

    class PhotoCaptureWriter( Thread ):

        def __init__( self, path, timestamp ):

            logger = logging.getLogger('capture.photo.writer.init' )

            logger.info( 'creating photo writer for {}.jpg...'.format(
                os.path.join( path, timestamp ) ) )

            self.path = path
            self.timestamp = timestamp
            self.daemon = True

        def run( self ):
            logger = logging.getLogger( 'capture.photo.writer.run' )

            filename = '{}/{}.mp4'.format( self.path, self.timestamp )

            logger.info( 'writing {}...'.format( filename ) )

            cv2.imwrite( filename, frame )

            logger.info( 'writing {} complete'.format( filename ) )

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )

    def append_motion( self, frame, w, h ):
        timestamp = datetime.now().strftime( self.ts_format )
        encoder = self.PhotoCaptureWriter( self.path, timestamp )
        encoder.start()

