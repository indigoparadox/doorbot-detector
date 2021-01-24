
import cv2
import logging
import os
import io
import shutil
from datetime import datetime
from threading import Thread
from ftplib import FTP
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

class Capture( object ):

    def __init__( self, **kwargs ):

        self.path = kwargs['path'] if 'path' in kwargs else '/tmp'
        self.backup_path = \
            kwargs['backuppath'] if 'backuppath' in kwargs else '/tmp'
        self.ts_format = kwargs['tsformat'] if 'tsformat' in kwargs else \
            '%Y-%m-%d-%H-%M-%S-%f'

    def start_motion( self, frame ):
        pass

    def process_motion( self, frame ):
        pass

class VideoCapture( Capture ):

    class VideoCaptureWriter( Thread ):
        def __init__( self, path, bkp, w, h, fps, ts, fourcc, container ):
            super().__init__()

            logger = logging.getLogger('capture.video.writer.init' )

            self.timestamp = ts
            self.path = path
            self.backup_path = bkp

            logger.debug( 'creating video writer for {}.mp4...'.format(
                os.path.join( self.path, self.timestamp ) ) )

            self.frames = []
            self.w = w
            self.h = h
            self.fps = fps
            self.fourcc = fourcc
            self.container = container
            self.daemon = True

        def upload_ftp( self, filepath  ):

            logger = logging.getLogger( 'capture.video.writer.ftp' )

            # Login and change to dest dir.
            pr = urlparse( self.path )
            logger.info( 'logging into ftp at {} as {}...'.format(
                pr.hostname, pr.username ) )
            ftp = FTP( host=pr.hostname, user=pr.username, passwd=pr.password )
            ftp.cwd( pr.path )

            logger.info( 'uploading {}...'.format( filepath ) )

            # Upload the file.
            with open( filepath, 'rb' ) as fp:
                dest_filename = os.path.basename( filepath )
                ftp.storbinary( 'STOR {}'.format( dest_filename ), fp )

        def run( self ):

            logger = logging.getLogger( 'capture.video.writer.run' )

            temp_dir = TemporaryDirectory()

            # Determine path for saved video/temporary video.
            filename = '{}.{}'.format( self.timestamp, self.container )
            filepath = filename
            if self.path.startswith( 'ftp:' ):
                filepath = os.path.join( temp_dir.name, filename )
            else:
                filepath = os.path.join( self.path, filename )

            logger.info( 'encoding {} ({} frames, {} fps)...'.format(
                filepath, len( self.frames ), self.fps ) )

            # Encode the video file.
            fourcc = cv2.VideoWriter_fourcc( *(self.fourcc) )
            encoder = \
                cv2.VideoWriter( filepath, fourcc, self.fps, (self.w, self.h) )
            for frame in self.frames:
                encoder.write( frame )
            encoder.release()

            # Try to upload file if remote path specified.
            if self.path.startswith( 'ftp:' ):
                try:
                    self.upload_ftp( filepath )

                    temp_dir.cleanup()
                except Exception as e:
                    logger.error( 'ftp upload failure: {}'.format( e ) )
                    backup_filepath = os.path.join( self.backup_path, filename )
                    logger.info( 'moving {} to {}...'.format( 
                        filepath, backup_filepath ) )
                    shutil.move( filepath, backup_filepath )

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
                self.path, self.backup_path, w, h, self.fps,
                timestamp, self.fourcc, self.container )

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

