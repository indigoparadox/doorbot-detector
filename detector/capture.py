
import logging
import os
import shutil
from datetime import datetime
from threading import Thread
from ftplib import FTP, FTP_TLS
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import cv2

class Capture( object ):

    ''' Abstract module for capturing and storing frames for archival. '''

    def __init__( self, **kwargs ):

        self.path = kwargs['path'] if 'path' in kwargs else '/tmp'
        self.backup_path = \
            kwargs['backuppath'] if 'backuppath' in kwargs else '/tmp'
        self.ts_format = kwargs['tsformat'] if 'tsformat' in kwargs else \
            '%Y-%m-%d-%H-%M-%S-%f'

    def handle_motion_frame( self, frame, width, height ):

        ''' Append a frame to the current animation, or handle it
        individually. '''

        raise Exception( 'not implemented!' )

    def finalize_motion( self, frame, width, height ):

        ''' Process the batch of recent motion frames into e.g. a video. '''

        raise Exception( 'not implemented!' )

class VideoCapture( Capture ):

    class VideoCaptureWriter( Thread ):
        def __init__( self, path, bkp, w, h, fps, ts, fourcc, cont, ftpssl ):
            super().__init__()

            logger = logging.getLogger('capture.video.writer.init' )

            self.timestamp = ts
            self.path = path
            self.backup_path = bkp
            self.ftp_ssl = ftpssl

            logger.debug( 'creating video writer for %s.mp4...',
                os.path.join( self.path, self.timestamp ) )

            self.frames = []
            self.w = w
            self.h = h
            self.fps = fps
            self.fourcc = fourcc
            self.container = cont
            self.daemon = True

        def upload_ftp( self, filepath ):

            ''' Upload the given file to the FTP server configured in the
            application configuration (path under [videocap]). '''

            logger = logging.getLogger( 'capture.video.writer.ftp' )

            # Login and change to dest dir.
            parsed = urlparse( self.path )
            logger.info( 'logging into ftp at %s as %s...',
                parsed.hostname, parsed.username )
            ftp = None
            if self.ftp_ssl:
                ftp = FTP_TLS( host=parsed.hostname )
            else:
                ftp = FTP( host=parsed.hostname )
            ftp.login( user=parsed.username, passwd=parsed.password )
            if self.ftp_ssl:
                ftp.prot_p()
            ftp.cwd( parsed.path )

            logger.info( 'uploading %s...', filepath )

            # Upload the file.
            with open( filepath, 'rb' ) as upload_file:
                dest_filename = os.path.basename( filepath )
                ftp.storbinary( 'STOR {}'.format( dest_filename ), upload_file )

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

            logger.info( 'encoding %s (%d frames, %d fps)...',
                filepath, len( self.frames ), self.fps )

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
                    logger.error( 'ftp upload failure: %s', e )
                    backup_filepath = os.path.join( self.backup_path, filename )
                    logger.info( 'moving %s to %s...', filepath, backup_filepath )
                    shutil.move( filepath, backup_filepath )

            logger.info( 'encoding %s completed', filename )

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )

        logger = logging.getLogger( 'capture.video.init' )
        logger.info( 'setting up video capture...' )

        self.ftp_ssl = True if 'ftpssl' in kwargs and \
            'true' == kwargs['ftpssl'] else False
        self.grace_remaining = 0
        self.grace_frames = int( kwargs['graceframes'] ) \
            if 'graceframes' in kwargs else 0
        self.fps = float( kwargs['fps'] ) if 'fps' in kwargs else 15.0
        self.fourcc = kwargs['fourcc'] if 'fourcc' in kwargs else 'mp4v'
        self.container = kwargs['container'] if 'container' in kwargs else 'mp4'

        self.encoder = None

    def _create_or_append_to_encoder( self, frame, width, height ):
        if None == self.encoder:
            timestamp = datetime.now().strftime( self.ts_format )
            self.encoder = self.VideoCaptureWriter(
                self.path, self.backup_path, width, height, self.fps,
                timestamp, self.fourcc, self.container, self.ftp_ssl )

        self.encoder.frames.append( frame )

    def handle_motion_frame( self, frame, width, height ):

        self._create_or_append_to_encoder( frame.copy(), width, height )

        # Start/reset grace countdown.
        self.grace_remaining = self.grace_frames

    def finalize_motion( self, frame, width, height ):
        if 0 < self.grace_remaining and None != self.encoder:
            # Append grace frame.
            self._create_or_append_to_encoder( frame.copy(), width, height )
            self.grace_remaining -= 1

        elif None != self.encoder:
            # Ship the frames off to a separate thread to write out.
            self.encoder.start()
            self.encoder = None

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

        pass
