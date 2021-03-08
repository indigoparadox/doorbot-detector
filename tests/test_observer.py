
import os
import sys
import unittest
import logging
from unittest import mock
from unittest.mock import patch, Mock, MagicMock, NonCallableMagicMock
from contextlib import contextmanager

from faker import Faker
import numpy.testing
try:
    from cv2 import cv2
except ImportError:
    import cv2

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )

from doorbot.observers.framebuffer import FramebufferProc
from doorbot.observers.reserver import ReserverHandler, ReserverProc
from doorbot.portability import image_to_jpeg
from fake_camera import FakeCamera

class TestObserver( unittest.TestCase ):

    def setUp( self ):
        self.fake = Faker()
        self.fake.add_provider( FakeCamera )

    def tearDown( self ):
        #self.mock_http.
        pass

    def create_reserver_handler( self, path, frame, remote_addr='127.0.0.1' ):
        ReserverHandler.__init__ = lambda w, x, y, z: None
        reserver = ReserverHandler( b'', ('', 0), None )
        reserver.server = Mock()
        reserver.server.logger = Mock()
        reserver.server.proc = ReserverProc()
        reserver.server.proc.get_frame = MagicMock()
        get_frame = reserver.server.proc.get_frame.return_value
        get_frame.__enter__ = MagicMock( return_value=frame )
        def reserver_loop_once():
            reserver.server.proc._running = False
            return True
        reserver.server.proc.frame_ready = Mock( side_effect=reserver_loop_once )
        reserver.client_address = (remote_addr,)
        reserver.request_version = Mock( return_value='HTTP/1.0' )
        reserver.wfile = Mock()
        reserver.path = path
        reserver.send_response = Mock()
        return reserver

    def test_framebuffer( self ):
        with patch( 'builtins.open' ) as mock_fb:
            frame = self.fake.random_image( 640, 480 )

            # Prepare the framebuffer.
            fb = FramebufferProc( width=320, height=240 )
            fb.get_frame = MagicMock()
            get_frame = fb.get_frame.return_value
            get_frame.__enter__ = MagicMock( return_value=frame )
            fb._running = True
            def fb_loop_once():
                fb._running = False
                return True

            # Prepare the frame to test against.
            fb.frame_ready = Mock( side_effect=fb_loop_once )
            frame_test = cv2.cvtColor( frame, cv2.COLOR_BGR2BGRA )
            frame_test = cv2.resize( frame_test, (320, 240) )

            fb.loop()

            # Check the results.
            mock_fb.assert_called_once_with( '/dev/fb0', 'rb+' )
            mock_write = mock_fb.return_value.__enter__.return_value.write
            mock_write.assert_called_once()
            numpy.testing.assert_array_equal( mock_write.call_args[0][0], frame_test )

    def test_reserver_jpg( self ):

        frame = self.fake.random_image( 640, 480 )
        reserver = self.create_reserver_handler( '/test.jpg', frame )
        jpg_test = image_to_jpeg( frame )
        reserver.do_GET()
        reserver.wfile.write.assert_called_with( jpg_test )

    def test_reserver_mjpg( self ):

        frame = self.fake.random_image( 640, 480 )
        reserver = self.create_reserver_handler( '/test.mjpg', frame )
        jpg_test = image_to_jpeg( frame )
        reserver.do_GET()
        reserver.wfile.write.assert_called_with( jpg_test )
