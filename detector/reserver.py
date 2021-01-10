
import logging
import time
import cv2
from threading import Thread, Lock
from http.server import BaseHTTPRequestHandler, HTTPServer

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
                ret, jpg = cv2.imencode( '.jpg', self.server._frame )
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

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

        self._source_lock = Lock()
        self._frame = None

    @property
    def frame( self ):
        return self._frame

    @frame.setter
    def frame( self, value ):
        with self._source_lock:
            self._frame = value

class ReserverThread( Thread ):

    def __init__( self, **kwargs ):
        super().__init__()
        self.daemon = True
        hostname = kwargs['hostname'] if 'hostname' in kwargs else '0.0.0.0'
        port = int( kwargs['port'] ) if 'port' in kwargs else 8888
        self.server = Reserver( (hostname, port), ReserverHandler )

    def run( self ):
        
        logger = logging.getLogger( 'reserver.run' )
        logger.debug( 'starting reserver...' )

        self.server.serve_forever()

