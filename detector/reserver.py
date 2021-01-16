
import logging
import time
import cv2
from threading import Thread, Lock
from http.server import BaseHTTPRequestHandler, HTTPServer

class ObserverThread( Thread ):

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
        self._source_lock = Lock()
        self._frame = None

class DisplayThread( ObserverThread ):

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )

        self.fb_path = kwargs['fbpath'] if 'fbpath' in kwargs else '/dev/fb0'

    def run( self ):

        while True:
            with open( '/dev/fb0', 'rb+' ) as fb:
                try:
                    self.frame = cv2.cvtColor( self.frame, cv2.COLOR_BGR2BGRA )
                    self.frame = cv2.resize( self.frame, (480, 320) )
                    fb.write( self.frame )
                except:
                    pass
            time.sleep( 1 )

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
            jpg = None
            try:
                ret, jpg = cv2.imencode( '.jpg', self.server.thread.frame )
            except Exception as e:
                #logger.error( e )
                time.sleep( 1 )
                continue
            self.wfile.write( '--jpgboundary'.encode( 'utf-8' ) )
            self.send_header( 'Content-type', 'image/jpeg' )
            self.send_header( 'Content-length', '{}'.format( jpg.size ) )
            self.end_headers()
            self.wfile.write( jpg.tostring() )
        
class Reserver( HTTPServer ):

    ''' This serves an mjpeg stream with what the detector sees. '''

    def __init__( self, thread, *args, **kwargs ):
        super().__init__( *args, **kwargs )

        self.thread = thread

class ReserverThread( ObserverThread ):

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )
        hostname = kwargs['listen'] if 'listen' in kwargs else '0.0.0.0'
        port = int( kwargs['port'] ) if 'port' in kwargs else 8888
        self.server = Reserver( self, (hostname, port), ReserverHandler )

    def run( self ):
        
        logger = logging.getLogger( 'reserver.run' )
        logger.debug( 'starting reserver...' )

        self.server.serve_forever()

