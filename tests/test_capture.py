
from datetime import datetime
from doorbot.capturers import Capture, CaptureWriter
import os
import sys
import unittest
import logging
import re
import tempfile
import shutil
import random
from threading import Thread, local

import memunit
from faker import Faker
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import ThreadedFTPServer
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )

from doorbot.capturers.video import VideoCapture
from doorbot.capturers.photo import PhotoCapture
from doorbot.portability import image_to_jpeg
from fake_camera import FakeCamera

RE_DURATION = re.compile( r'^- Duration:\s*(?P<sec>[0-9]*)\s*sec(\s*(?P<ms>[0-9]*)\s*ms)?' )
RE_WIDTH = re.compile( r'^- Image width:\s*(?P<width>[0-9]*)\s*pixels' )
RE_HEIGHT = re.compile( r'^- Image height:\s*(?P<height>[0-9]*)\s*pixels' )

class TestCapture( unittest.TestCase ):

    def setUp(self) -> None:

        self.fake = Faker()
        self.fake.add_provider( FakeCamera )

        self.temp_folder = tempfile.mkdtemp()
        self.temp_upload_file_path = None

        self.ftp_auth = DummyAuthorizer()
        self.ftp_auth.add_user( 'test', 'test', self.temp_folder, 'elrmw' )
        self.ftp_handler = FTPHandler
        self.ftp_handler.authorizer = self.ftp_auth
        self.ftp_server = None
        while not self.ftp_server:
            self.ftp_port = random.randint( 50000, 60000 )
            try:
                self.ftp_server = ThreadedFTPServer(
                    ('localhost', self.ftp_port), self.ftp_handler )
            except Exception as exc:
                print( '{} error creating FTP server: {}; retrying...'.format(
                    type( exc ), exc ) )
                self.ftp_server = None
        self.ftp_thread = Thread( target=self.ftp_server.serve_forever )
        self.ftp_thread.start()

        logging.getLogger( '' ).setLevel( logging.DEBUG )

    def tearDown(self) -> None:

        self.ftp_server.close_all()
        shutil.rmtree( self.temp_folder )
        if self.temp_upload_file_path:
            os.unlink( self.temp_upload_file_path )

    def test_capture_upload( self ):
        frame_jpg = image_to_jpeg( self.fake.random_image( 640, 480 ) )
        self.temp_upload_file_path = tempfile.mktemp( suffix='.jpg' )
        with open( self.temp_upload_file_path, 'wb' ) as temp_file:
            temp_file.write( frame_jpg )

        nowdate = datetime.now()
        nowstamp = nowdate.strftime( '%Y-%m-%d-%H-%M-%S-%f' )
        ftp_path = 'ftp://test:test@localhost:{}/dev/%date%'.format( self.ftp_port )
        print( ftp_path )
        capturer_args = {
            'path': ftp_path
        }
        capturer = CaptureWriter( nowstamp, 640, 480, **capturer_args )
        capturer.upload_ftp( self.temp_upload_file_path )

        # Verify file was uploaded correctly.
        upload_local_dest = os.path.join(
            self.temp_folder,
            'dev',
            nowdate.strftime( '%Y-%m-%d' ),
            os.path.basename( self.temp_upload_file_path ) )
        self.assertTrue( os.path.exists( upload_local_dest ) )
        local_stat = os.stat( self.temp_upload_file_path )
        remote_stat = os.stat( upload_local_dest )
        self.assertEqual( local_stat.st_size, remote_stat.st_size )

    def test_capture_photo( self ):

        with self.fake.directory() as capture_path:

            config = {
                'enable': 'true',
                'backuppath': capture_path,
                'path': capture_path,
                'multiproc': 'false'
            }

            capturer = PhotoCapture( **config )

            for i in range( 10 ):
                frame = None
                frame = self.fake.random_image( 640, 480 )
                capturer.handle_motion_frame( frame )

            capturer.finalize_motion( None )

            self.assertEqual( len( os.listdir( capture_path ) ), 10 )

    @memunit.assert_lt_mb( 300 )
    def test_capture_video( self ):

        with self.fake.directory() as capture_path:

            config = {
                'enable': 'true',
                'graceframes': '10',
                'backuppath': capture_path,
                'path': capture_path,
                'fps': '5.0',
                'fourcc': 'mp4v',
                'container': 'mp4',
                'multiproc': 'false'
            }

            capturer = VideoCapture( **config )

            for i in range( 5 ):
                frame = None
                self.assertEqual( capturer.frames_count, 0 )
                fc_check = 0
                for j in range( 0, 200 ):
                    frame = self.fake.random_image( 640, 480 )
                    capturer.handle_motion_frame( frame )
                    fc_check += 1
                    if fc_check > 100:
                        fc_check = 0
                    else:
                        self.assertEqual( capturer.frames_count, fc_check )

                capturer.finalize_motion( None )
                self.assertEqual( capturer.frames_count, 0 )

            # Verify the video files.
            video_count : int = 0
            for entry in os.scandir( capture_path ):
                if entry.name.endswith( '.mp4' ):
                    width : int = 0
                    height : int = 0
                    sec : int = 0
                    #ms : int = 0
                    video_count += 1
                    filename = os.path.join( capture_path, entry.name )
                    parser = createParser( filename )
                    metadata = extractMetadata( parser )
                    text = metadata.exportPlaintext()
                    for line in text:
                        match = RE_DURATION.match( line )
                        if match:
                            sec = int( match.group('sec') )
                            #ms = int( match.group('ms') )
                            continue

                        match = RE_WIDTH.match( line )
                        if match:
                            width = int( match.group('width') )
                            continue

                        match = RE_HEIGHT.match( line )
                        if match:
                            height = int( match.group('height') )

                    self.assertEqual( width, 640 )
                    self.assertEqual( height, 480 )
                    self.assertIn( sec, [19, 20] )
                    #self.assertEqual( ms, 190 )

            self.assertEqual( video_count, 10 )
