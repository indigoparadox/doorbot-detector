
import os
import logging
from queue import Empty
import shutil
import multiprocessing
from datetime import datetime
from ftplib import FTP, FTP_TLS
from ftplib import all_errors as FTPExceptions
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

import numpy

try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.capturers import Capture

class VideoLengthException( Exception ):
    pass

class VideoCaptureWriterProcess( multiprocessing.Process ):
    def __init__( self, writer ):
        super().__init__()
        self.frames = multiprocessing.Queue()
        self.writer = writer
        self.writer.process = self
        self.logger = logging.getLogger( 'capture.process' )

    def add_frame( self, frame ):
        self.frames.put_nowait( frame )

    def run( self ):

        frame_array = []
        try:
            frame = self.frames.get( block=True, timeout=1.0 )
            while isinstance( frame, numpy.ndarray ):
                self.writer.frame_array.insert( 0, frame )
                frame = self.frames.get( block=True, timeout=1.0 )
        except Empty:
            self.logger.info( 'encoder thread received %d frames', len( frame_array ) )

        self.writer.start()

class VideoCaptureWriter( object ):
    def __init__( self, path, bkp, width, height, fps, ts, fourcc, cont, ftpssl ):
        super().__init__()

        logger = logging.getLogger('capture.video.writer.init' )

        self.timestamp = ts
        self.path = path
        self.backup_path = bkp
        self.ftp_ssl = ftpssl

        logger.debug( 'creating video writer for %s.mp4...',
            os.path.join( self.path, self.timestamp ) )

        self.width = width
        self.height = height
        self.fps = fps
        self.fourcc = fourcc
        self.container = cont
        self.frame_array = []

        self.process = None

    def add_frame( self, frame ):
        self.frame_array.append( frame )

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

    def start( self ):

        # This will run in its own process. The queue is used to pass frames in.

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
            filepath, len( self.frame_array ), self.fps )

        # Encode the video file.
        fourcc = cv2.VideoWriter_fourcc( *(self.fourcc) )
        encoder = \
            cv2.VideoWriter( filepath, fourcc, self.fps, (self.width, self.height) )
        while 0 < len( self.frame_array ):
            encoder.write( self.frame_array.pop() )
        encoder.release()

        # Try to upload file if remote path specified.
        if self.path.startswith( 'ftp:' ):
            try:
                self.upload_ftp( filepath )

                temp_dir.cleanup()
            except Exception as exc:
                logger.error( 'ftp upload failure: %s', exc )
                backup_filepath = os.path.join( self.backup_path, filename )
                logger.info( 'moving %s to %s...', filepath, backup_filepath )
                shutil.move( filepath, backup_filepath )
                temp_dir.cleanup()

        logger.info( 'encoding %s completed', filename )

class VideoCapture( Capture ):

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )

        self.logger = logging.getLogger( 'capture.video' )
        self.logger.info( 'setting up video capture...' )

        self.ftp_ssl = True if 'ftpssl' in kwargs and \
            'true' == kwargs['ftpssl'] else False
        self.grace_remaining = 0
        self.grace_frames = int( kwargs['graceframes'] ) \
            if 'graceframes' in kwargs else 0
        self.fps = float( kwargs['fps'] ) if 'fps' in kwargs else 15.0
        self.fourcc = kwargs['fourcc'] if 'fourcc' in kwargs else 'mp4v'
        self.container = kwargs['container'] if 'container' in kwargs else 'mp4'
        self.frames_count = 0
        self.max_frames = int( kwargs['maxframes'] ) if 'maxframes' in kwargs else 100
        self.multiproc = True if 'multiproc' in kwargs and 'true' == kwargs['multiproc'] else False
        self.writer = None

    def _create_or_append_to_writer( self, frame, width, height ):
        if None == self.writer:
            timestamp = datetime.now().strftime( self.ts_format )
            writer = VideoCaptureWriter(
                self.path, self.backup_path, width, height, self.fps,
                timestamp, self.fourcc, self.container, self.ftp_ssl )
            if self.multiproc:
                self.writer = VideoCaptureWriterProcess( writer )
            else:
                self.writer = writer
            
        self.writer.add_frame( frame )

        self.frames_count += 1

    def handle_motion_frame( self, frame, width, height ):

        if self.frames_count > self.max_frames:
            self.grace_remaining = 0
            raise VideoLengthException(
                'motion exceeded maximum {} frames'.format(
                self.max_frames ) )
        else:
            self._create_or_append_to_writer( frame.copy(), width, height )

            # Start/reset grace countdown.
            self.grace_remaining = self.grace_frames

    def finalize_motion( self, frame, width, height ):
        if 0 < self.grace_remaining and None != self.writer:
            # Append grace frame.
            self._create_or_append_to_writer( frame.copy(), width, height )
            self.grace_remaining -= 1

        elif None != self.writer:
            # Ship the frames off to a separate thread to write out.
            self.frames_count = 0
            self.writer.start()
            self.writer = None

PLUGIN_TYPE = 'capturers'
PLUGIN_CLASS = VideoCapture
