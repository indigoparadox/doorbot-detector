
import os
import sys
import unittest

import memunit
from faker import Faker
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import ThreadedFTPServer

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )

from doorbot.capturers.video import VideoCapture, VideoLengthException
from doorbot.capturers.photo import PhotoCapture
from fake_camera import FakeCamera

from hachoir.parser import createParser
from hachoir.core.tools import makePrintable
from hachoir.metadata import extractMetadata
from hachoir.core.i18n import getTerminalCharset

class TestCapture( unittest.TestCase ):

    def setUp(self) -> None:

        self.fake = Faker()
        self.fake.add_provider( FakeCamera )

        self.ftp_auth = DummyAuthorizer()
        self.ftp_auth.add_user( 'test', 'test', '/tmp' )
        self.ftp_handler = FTPHandler
        self.ftp_handler.authorizer = self.ftp_auth
        self.ftp_server = ThreadedFTPServer( ('127.0.0.1', 50212), self.ftp_handler )
        self.ftp_server.serve_forever( blocking=False )

        return super().setUp()

    def tearDown(self) -> None:

        self.ftp_server.close_all()

        return super().tearDown()

    def test_capture_upload( self ):

        pass

    def test_capture_photo( self ):

        pass

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

            for i in range( 1 ):
                print( 'video {}'.format( i ) )
                frame = None
                for j in range( 200 ):
                    try:
                        frame = self.fake.random_image( 640, 480 )
                        capturer.handle_motion_frame( frame, 640, 480 )
                    except VideoLengthException as exc:
                        print( exc )
                        capturer.finalize_motion( frame, 640, 480 )

            capturer.finalize_motion( frame, 640, 480 )

            for entry in os.scandir( capture_path ):
                if entry.name.endswith( '.mp4' ):
                    filename = os.path.join( capture_path, entry.name )
                    parser = createParser( filename )
                    metadata = extractMetadata( parser )
                    text = metadata.exportPlaintext()
                    charset = getTerminalCharset()
                    for line in text:
                        print( makePrintable( line, charset ) )
