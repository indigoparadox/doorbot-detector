
import logging
import os
import multiprocessing
import shutil
import time
from queue import Empty
from ftplib import FTP, FTP_TLS
from ftplib import all_errors, error_perm
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

    def __init__( self, timestamp : str, width, height, **kwargs ):

        self.logger = logging.getLogger( 'capture.writer' )

        self.timestamp = timestamp
        self.ts_format = kwargs['tsformat'] if 'tsformat' in kwargs else \
            '%Y-%m-%d-%H-%M-%S-%f'
        self.path = kwargs['path'] if 'path' in kwargs else '/tmp'
        self.backup_path = \
            kwargs['backuppath'] if 'backuppath' in kwargs else self.path
        self.ftp_ssl = bool( 'ftpssl' in kwargs and kwargs['ftpssl'] )

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

    def upload_ftp_or_backup( self, filepath, filename, temp_dir ):
        #try:
        self.upload_ftp( filepath )
        temp_dir.cleanup()
        #except (ConnectionRefusedError,) as exc:
        #    self.logger.error( 'ftp upload failure: %s', exc )
        #    backup_filepath = os.path.join( self.backup_path, filename )
        #    self.logger.info( 'moving %s to %s...', filepath, backup_filepath )
        #    shutil.move( filepath, backup_filepath )
        #    temp_dir.cleanup()

    def login_ftp( self ) -> FTP:
        # FTP login.
        parsed = urlparse( self.path )
        self.logger.info( 'logging into ftp at %s as %s...',
            parsed.hostname, parsed.username )
        ftp = None
        if self.ftp_ssl:
            ftp_class = FTP_TLS
        else:
            ftp_class = FTP
        ftp = ftp_class()
        connect_args = { 'host': parsed.hostname }
        if parsed.port:
            connect_args['port'] = parsed.port
        ftp.connect( **connect_args )
        ftp.login( user=parsed.username, passwd=parsed.password )
        if self.ftp_ssl:
            ftp.prot_p()
        return ftp

    def chdir_ftp( self, ftp : FTP, path ):

        if not path:
            return

        try:
            ftp.cwd( path )
        except error_perm:
            parent_path = os.path.dirname( path )
            self.chdir_ftp( ftp, parent_path )
            self.logger.info( 'creating missing remote directory: %s', path )
            try:
                ftp.mkd( path )
            except error_perm:
                pass
            ftp.cwd( path )

    def upload_ftp( self, filepath ):

        ''' Upload the given file to the FTP server configured in the
        application configuration (path under [videocap]). '''

        ftp = self.login_ftp()

        # Tokenize FTP CWD path and create missing directories.
        parsed = urlparse( self.path )
        cwd_path = parsed.path
        datestamp = datetime.strftime(
            datetime.strptime( self.timestamp, self.ts_format ), '%Y-%m-%d' )
        cwd_path = cwd_path.replace( '%date%', datestamp )

        self.chdir_ftp( ftp, cwd_path )

        self.logger.info( 'uploading %s to %s...', filepath, cwd_path )

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

        kickstart = True
        frame = None
        while isinstance( frame, self.frame_type ) or kickstart:
            try:
                frame = self.frames.get( block=True, timeout=1.0 )
                self.writer.frame_array.insert( 0, frame )
                kickstart = False
            except Empty:
                break

        self.logger.info( 'encoder thread received %d frames',
            len( self.writer.frame_array ) )
        self.frames.close()

        self.writer.start()
        self.writer = None
