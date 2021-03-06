
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from doorbot.portability import image_to_jpeg
from doorbot.observers import ObserverProc
from doorbot.util import FPSTimer

class ReserverHandler( BaseHTTPRequestHandler ):

    def do_GET( self ): # pylint: disable=invalid-name

        self.server.logger.debug( 'connection from %s...', self.address_string() )

        if self.path.endswith( '.jpg' ) or \
        self.path.endswith( '.jpeg' ):
            return self.serve_jpeg()
        elif self.path.endswith( '.mjpg' ) or \
        self.path.endswith( '.mjpeg' ):
            return self.serve_mjpeg()

    def log_message( self, format, *args ): # pylint: disable=redefined-builtin
        return

    def serve_jpeg( self ):

        if not self.server.proc.frame_ready:
            self.server.logger.error( 'frame not ready' )
            self.send_response( 500 )
            return

        jpg = None
        with self.server.proc.get_frame() as orig_frame:
            jpg = image_to_jpeg( orig_frame )

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

        timer_kwargs = {}
        if self.server.fps:
            timer_kwargs['fps'] = self.server.fps

        timer = FPSTimer( self, **timer_kwargs )
        while self.server.proc.running:
            timer.loop_timer_start()
            jpg = None

            if not self.server.proc.frame_ready():
                self.server.logger.debug( 'waiting for frame...' )
                timer.loop_timer_end()
                continue

            with self.server.proc.get_frame() as orig_frame:
                jpg = image_to_jpeg( orig_frame )

            try:
                self.wfile.write( '--jpgboundary'.encode( 'utf-8' ) )
                self.send_header( 'Content-type', 'image/jpeg' )
                self.send_header( 'Content-length', '{}'.format( len( jpg ) ) )
                self.end_headers()
                self.wfile.write( jpg )
                timer.loop_timer_end()
            except BrokenPipeError:
                self.server.logger.info( 'client %s disconnected (thread %d)',
                    client_addr, threading.get_ident() )
                return

class Reserver( ThreadingMixIn, HTTPServer ):

    ''' This serves an mjpeg stream with what the detector sees. '''

    def __init__( self, thread, instance_name, fps, *args, **kwargs ):
        super().__init__( *args, **kwargs )

        self.daemon_threads = True
        self.logger = logging.getLogger( 'observer.reserver.{}'.format( instance_name ) )
        self.fps = fps

        self.proc = thread

class ReserverProc( ObserverProc ):

    def __init__( self, instance_name, **kwargs ):

        #logger = logging.getLogger( 'observer.reserver.init' )

        #logger.debug( 'setting up reserver...' )

        super().__init__( instance_name, **kwargs )
        self._hostname = kwargs['listen'] if 'listen' in kwargs else '0.0.0.0'
        self._port = int( kwargs['port'] ) if 'port' in kwargs else 8888
        self._server : Reserver
        self.fps = float( kwargs['fps'] ) if 'fps' in kwargs else None

    def loop( self ):

        #logger = logging.getLogger( 'reserver.run' )
        #logger.debug( 'starting reserver...' )

        self.logger.info( 'setting up reserver on port %d...', self._port )
        self._server = Reserver( self, self.instance_name, self.fps,
            (self._hostname, self._port), ReserverHandler )

        self._server.serve_forever()
        self.running = False

PLUGIN_CLASS = ReserverProc # pylint: disable=invalid-name
PLUGIN_TYPE = 'observers'
