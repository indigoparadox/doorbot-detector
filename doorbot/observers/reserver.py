
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from doorbot.portability import image_to_jpeg
from doorbot.observers import ObserverThread

class ReserverHandler( BaseHTTPRequestHandler ):

    def do_GET( self ):

        self.server.logger.debug( 'connection from %s...', self.address_string() )

        if self.path.endswith( '.jpg' ):
            return self.serve_jpeg()
        else:
            return self.serve_mjpeg()

    def log_message( self, format, *args ):
        return

    def serve_jpeg( self ):

        if not self.server.thread._frame.frame_ready:
            self.server.logger.error( 'frame not ready' )
            self.send_response( 500 )
            return

        # TODO: Superfluous copy.
        frame = None
        with self.server.thread._frame.get_frame() as orig_frame:
            frame = orig_frame.copy()

        #self.server.thread.draw_overlay( frame )

        jpg = image_to_jpeg( frame )

        self.send_response( 200 )
        self.send_header( 'Content-type', 'image/jpeg' )
        self.send_header( 'Content-length', len( jpg ) )
        self.end_headers()

        self.wfile.write( jpg )

    def serve_mjpeg( self ):

        # Crude mjpeg server.

        self.send_response( 200 )
        self.send_header(
            'Content-type',
            'multipart/x-mixed-replace; boundary=--jpgboundary'
        )
        self.end_headers()

        client_addr = self.client_address[0]

        self.server.logger.info( 'serving stream to client %s (thread %d)',
            client_addr, threading.get_ident() )

        jpg = None

        while self.server.thread.running:
            self.server.thread.timer.loop_timer_start()
            jpg = None

            if not self.server.thread._frame.frame_ready:
                self.server.logger.debug( 'waiting for frame...' )
                self.server.thread.timer.loop_timer_end()
                continue

            # TODO: Superfluous copy.
        
            with self.server.thread._frame.get_frame() as orig_frame:
                jpg = image_to_jpeg( orig_frame )

            try:
                self.wfile.write( '--jpgboundary'.encode( 'utf-8' ) )
                self.send_header( 'Content-type', 'image/jpeg' )
                self.send_header( 'Content-length', '{}'.format( len( jpg ) ) )
                self.end_headers()
                self.wfile.write( jpg )
                self.server.thread.timer.loop_timer_end()
            except BrokenPipeError:
                self.server.logger.info( 'client %s disconnected (thread %d)',
                    client_addr, threading.get_ident() )
                return

class Reserver( ThreadingMixIn, HTTPServer ):

    ''' This serves an mjpeg stream with what the detector sees. '''

    def __init__( self, thread, *args, **kwargs ):
        super().__init__( *args, **kwargs )

        self.daemon_threads = True
        self.logger = logging.getLogger( 'observer.reserver' )

        self.thread = thread

class ReserverThread( ObserverThread ):

    def __init__( self, **kwargs ):

        #logger = logging.getLogger( 'observer.reserver.init' )

        #logger.debug( 'setting up reserver...' )

        super().__init__( **kwargs )
        hostname = kwargs['listen'] if 'listen' in kwargs else '0.0.0.0'
        port = int( kwargs['port'] ) if 'port' in kwargs else 8888
        self.server = Reserver( self, (hostname, port), ReserverHandler )

    def run( self ):

        #logger = logging.getLogger( 'reserver.run' )
        #logger.debug( 'starting reserver...' )

        self.server.serve_forever()

PLUGIN_CLASS = ReserverThread
PLUGIN_TYPE = 'observers'
