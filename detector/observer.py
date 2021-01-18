
import logging
import time
import cv2
import threading
from socketserver import ThreadingMixIn
from http.server import BaseHTTPRequestHandler, HTTPServer
from .util import FPSTimer, FrameLock
from contextlib import contextmanager

class ObserverThread( threading.Thread ):

    def set_frame( self, value ):
        self._frame.set_frame( value )

    def __init__( self, **kwargs ):
        super().__init__()
        self.daemon = True
        self._frame = FrameLock()
        self.timer = FPSTimer( self, **kwargs )
        self.running = True
        self.overlay = kwargs['overlay'] if 'overlay' in kwargs else None

    def draw_overlay( self, frame ):

        ''' Draw overlay on the frame. Different observers need different
        processing, so they should call this on the frame just before displaying
        it. '''

        if not self.overlay:
            return

        font = cv2.FONT_HERSHEY_SIMPLEX
        org = (10, 20)
        text = self.overlay.split( "\\n" )
        scale = 0.5
        color = (255, 255, 255)
        thickness = 1
        for line in text:
            line = self.cam.overlays.line( line )
            cv2.putText(
                frame, line, org, font, scale, color, thickness, cv2.LINE_AA )
            org = (org[0], org[1] + 20)

class FramebufferThread( ObserverThread ):

    def __init__( self, **kwargs ):

        logger = logging.getLogger( 'observer.framebuffer.init' )

        logger.debug( 'setting up framebuffer...' )
        
        super().__init__( **kwargs )

        self.path = kwargs['path'] if 'path' in kwargs else '/dev/fb0'
        self.width = int( kwargs['width'] ) if 'width' in kwargs else None
        self.height = int( kwargs['height'] ) if 'height' in kwargs else None

    def run( self ):

        logger = logging.getLogger( 'observer.framebuffer.run' )

        while self.running:
            self.timer.loop_timer_start()
            
            if not self._frame.ready:
                logger.debug( 'waiting for frame...' )
                self.timer.loop_timer_end()
                continue

            with open( self.path, 'rb+' ) as fb:
                #try:
                frame = None
                with self._frame.get_frame() as fm:
                    frame = fm.copy()

                # Process the image for the framebuffer.
                frame = cv2.cvtColor( frame, cv2.COLOR_BGR2BGRA )
                if None != self.width and None != self.height:
                    frame = cv2.resize(
                        frame, (self.width, self.height) )

                self.draw_overlay( frame )

                fb.write( frame )
                #except Exception as e:
                #    logger.warn( e )

            self.timer.loop_timer_end()

class ReserverHandler( BaseHTTPRequestHandler ):

    def do_GET( self ):

        logger = logging.getLogger( 'reserver.get' )

        logger.debug( 'connection from {}...'.format( self.address_string() ) )

        # Crude mjpeg server.

        self.send_response( 200 )
        self.send_header(
            'Content-type',
            'multipart/x-mixed-replace; boundary=--jpgboundary'
        )
        self.end_headers()

        while self.server.thread.running:
            self.server.thread.timer.loop_timer_start()
            jpg = None

            if not self.server.thread._frame.ready:
                logger.debug( 'waiting for frame...' )
                self.server.thread.timer.loop_timer_end()
                continue

            frame = None
            with self.server.thread._frame.get_frame() as fm:
                frame = fm.copy()

            self.server.thread.draw_overlay( frame )

            ret, jpg = cv2.imencode( '.jpg', fm )
            self.wfile.write( '--jpgboundary'.encode( 'utf-8' ) )
            self.send_header( 'Content-type', 'image/jpeg' )
            self.send_header( 'Content-length', '{}'.format( jpg.size ) )
            self.end_headers()
            self.wfile.write( jpg.tostring() )
            self.server.thread.timer.loop_timer_end()
        
class Reserver( ThreadingMixIn, HTTPServer ):

    ''' This serves an mjpeg stream with what the detector sees. '''

    def __init__( self, thread, *args, **kwargs ):
        super().__init__( *args, **kwargs )

        self.thread = thread

class ReserverThread( ObserverThread ):

    def __init__( self, **kwargs ):

        logger = logging.getLogger( 'observer.reserver.init' )

        logger.debug( 'setting up reserver...' )
        
        super().__init__( **kwargs )
        hostname = kwargs['listen'] if 'listen' in kwargs else '0.0.0.0'
        port = int( kwargs['port'] ) if 'port' in kwargs else 8888
        self.server = Reserver( self, (hostname, port), ReserverHandler )

    def run( self ):
        
        logger = logging.getLogger( 'reserver.run' )
        logger.debug( 'starting reserver...' )

        self.server.serve_forever()

