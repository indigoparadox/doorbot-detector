
import logging
import time
import cv2
import threading
from socketserver import ThreadingMixIn
from http.server import BaseHTTPRequestHandler, HTTPServer
from .timer import FPSTimer

class ObserverThread( threading.Thread ):

    @property
    def frame( self ):
        return self._frame

    @frame.setter
    def frame( self, value ):
        with self._source_lock:
            self._frame = value

    def __init__( self, **kwargs ):
        super().__init__()
        self.daemon = True
        self._source_lock = threading.Lock()
        self._frame = None
        self.timer = FPSTimer( self, **kwargs )

class FramebufferThread( ObserverThread ):

    def __init__( self, **kwargs ):

        logger = logging.getLogger( 'observer.framebuffer.init' )

        logger.debug( 'setting up framebuffer...' )
        
        super().__init__( **kwargs )

        self.fb_path = kwargs['fbpath'] if 'fbpath' in kwargs else '/dev/fb0'
        self.width = int( kwargs['width'] ) if 'width' in kwargs else None
        self.height = int( kwargs['height'] ) if 'height' in kwargs else None

    def run( self ):

        logger = logging.getLogger( 'observer.framebuffer.run' )

        while True:
            self.timer.loop_timer_start()
            with open( '/dev/fb0', 'rb+' ) as fb:
                try:
                    # Process the image for the framebuffer.
                    self.frame = cv2.cvtColor( self.frame, cv2.COLOR_BGR2BGRA )
                    if None != self.width and None != self.height:
                        self.frame = cv2.resize(
                            self.frame, (self.width, self.height) )

                    fb.write( self.frame )
                except Exception as e:
                    logger.warn( e )
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

        while True:
            self.server.thread.timer.loop_timer_start()
            jpg = None
            try:
                ret, jpg = cv2.imencode( '.jpg', self.server.thread.frame )
            except Exception as e:
                logger.warning( 'encoder error: {} (thread {})'.format(
                    e, threading.get_ident() ) )
                time.sleep( 1 )
                continue
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

