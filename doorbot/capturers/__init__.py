
import logging
import os
import multiprocessing
import shutil
import time
from queue import Empty
from ftplib import FTP, FTP_TLS
from ftplib import all_errors as FTPExceptions
from urllib.parse import urlparse
from datetime import datetime

class Capture( object ):

    ''' Abstract module for capturing and storing frames for archival. '''

    def __init__( self, frame_type : type, **kwargs ):

        self.ts_format = kwargs['tsformat'] if 'tsformat' in kwargs else \
            '%Y-%m-%d-%H-%M-%S-%f'

        self.capture_writer_type = lambda x, y, z, a, b, c: None
        self.capture_writer_proc_type = lambda x: None
        self.multiproc = False if 'multiproc' in kwargs \
            and 'false' == kwargs['multiproc'] else True
        self.writer = None
        self.frame_type = frame_type
        self.kwargs = kwargs

    def create_or_append_to_writer( self, frame, writer_type ):
        if None == self.writer:
            timestamp = datetime.now().strftime( self.ts_format )
            writer = writer_type( timestamp,
                frame.shape[1], frame.shape[0], **self.kwargs )
            if self.multiproc:
                self.writer = CaptureWriterProcess( writer, self.frame_type )
            else:
                self.writer = writer

        self.writer.add_frame( frame )

    def handle_motion_frame( self, frame ):

        ''' Append a frame to the current animation, or handle it
        individually. '''

        raise Exception( 'not implemented!' )

    def finalize_motion( self, frame ):

        ''' Process the batch of recent motion frames into e.g. a video. '''

        raise Exception( 'not implemented!' )

class CaptureWriter( object ):

    def __init__( self, timestamp, width, height, **kwargs ):
        super().__init__()

        logger = logging.getLogger('capture.video.writer.init' )

        self.timestamp = timestamp
        self.path = kwargs['path'] if 'path' in kwargs else '/tmp'
        self.backup_path = \
            kwargs['backuppath'] if 'backuppath' in kwargs else self.path
        self.ftp_ssl = bool( 'ftpssl' in kwargs and kwargs['ftpssl'] )

        logger.debug( 'creating video writer for %s.mp4...',
            os.path.join( self.path, self.timestamp ) )

        self.width = width
        self.height = height
        self.fps = float( kwargs['fps'] ) if 'fps' in kwargs else 15.0
        self.fourcc = kwargs['fourcc'] if 'fourcc' in kwargs else 'mp4v'
        self.container = kwargs['container'] if 'container' in kwargs else 'mp4'

        self.frame_array = []
        self.process = None

    def add_frame( self, frame ):
        self.frame_array.append( frame )

    def start( self ):

        ''' Implementation should override this and begin processing. '''

        pass

    def upload_ftp_or_backup( self, filepath, filename, temp_dir ):
        try:
            self.upload_ftp( filepath )
            temp_dir.cleanup()
        except Exception as exc:
            self.logger.error( 'ftp upload failure: %s', exc )
            backup_filepath = os.path.join( self.backup_path, filename )
            self.logger.info( 'moving %s to %s...', filepath, backup_filepath )
            shutil.move( filepath, backup_filepath )
            temp_dir.cleanup()

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

class CaptureWriterProcess( multiprocessing.Process ):
    def __init__( self, writer : CaptureWriter, frame_type : type ):
        super().__init__()
        self.frames = multiprocessing.Queue()
        self.writer = writer
        self.writer.process = self
        self.logger = logging.getLogger( 'capture.process' )
        self.frame_type = frame_type

    def add_frame( self, frame ):
        self.frames.put_nowait( frame )

    def run( self ):

        #max_dry_hits = 10
        #dry_hits = 0
        kickstart = True
        frame = None
        while isinstance( frame, self.frame_type ) or kickstart:
            try:
                frame = self.frames.get( block=True, timeout=1.0 )
                self.writer.frame_array.insert( 0, frame )
                #dry_hits = 0
                kickstart = False
            except Empty:
                #if max_dry_hits <= dry_hits:
                break
                #else:
                #    time.sleep( 0.1 )
                #    dry_hits += 1

        self.logger.info( 'encoder thread received %d frames',
            len( self.writer.frame_array ) )
        self.frames.close()

        self.writer.start()
        self.writer = None
