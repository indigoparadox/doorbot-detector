
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
        self.highlights = kwargs['highlight'].split( ',' ) \
            if 'highlight' in kwargs else []
        self.overlay_coords = \
            tuple( [int( x ) for x in kwargs['overlaycoords'].split( ',' )] ) \
            if 'overlaycoords' in kwargs else (10, 10)
        self.overlay_color = \
            tuple( [int( x ) for x in kwargs['overlaycolor'].split( ',' )] ) \
            if 'overlaycolor' in kwargs else (255, 255, 255)
        self.overlay_scale = float( kwargs['overlayscale'] ) \
            if 'overlayscale' in kwargs else 0.5
        self.overlay_thickness = int( kwargs['overlaythickness'] ) \
            if 'overlaythickness' in kwargs else 1
        self.overlay_font = \
            getattr( cv2, 'FONT_{}'.format( kwargs['overlayfont'] ) ) \
            if 'overlayfont' in kwargs else cv2.FONT_HERSHEY_SIMPLEX

    def draw_overlay( self, frame ):

        ''' Draw overlay on the frame. Different observers need different
        processing, so they should call this on the frame just before displaying
        it. '''

        for hl in self.highlights:
            if hl in self.cam.overlays.highlights and \
            'boxes' in self.cam.overlays.highlights[hl]:
                for bx in self.cam.overlays.highlights[hl]['boxes']:
                    cv2.rectangle( frame,
                        (bx['x1'], bx['y1']),
                        (bx['x2'], bx['y2']), bx['color'], 3 )

        if not self.overlay:
            return

        text = self.overlay.split( "\\n" )
        org = self.overlay_coords
        for line in text:
            line = self.cam.overlays.line( line )
            cv2.putText(
                frame, line, org, self.overlay_font,
                self.overlay_scale, self.overlay_color, self.overlay_thickness,
                cv2.LINE_AA )
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
            
            if not self._frame.frame_ready:
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

        if self.path.endswith( '.jpg' ):
            return self.serve_jpeg()
        else:
            return self.serve_mjpeg()

    def log_message(self, format, *args):
        return

    def serve_jpeg( self ):

        if not self.server.thread._frame.frame_ready:
            logger.error( 'frame not ready' )
            self.send_response( 500 )
            return

        self.send_response( 200 )
        self.send_header( 'Content-type', 'image/jpeg' )
        self.end_headers()

        frame = None
        with self.server.thread._frame.get_frame() as fm:
            frame = fm.copy()

        self.server.thread.draw_overlay( frame )

        ret, jpg = cv2.imencode( '.jpg', frame )
        self.wfile.write( jpg.tostring() )

    def serve_mjpeg( self ):

        logger = logging.getLogger( 'reserver.get.mjpeg' )

        # Crude mjpeg server.

        self.send_response( 200 )
        self.send_header(
            'Content-type',
            'multipart/x-mixed-replace; boundary=--jpgboundary'
        )
        self.end_headers()

        client_addr = self.client_address[0]

        logger.info( 'serving stream to client {} (thread {})'.format(
            client_addr, threading.get_ident() ) )

        while self.server.thread.running:
            self.server.thread.timer.loop_timer_start()
            jpg = None

            if not self.server.thread._frame.frame_ready:
                logger.debug( 'waiting for frame...' )
                self.server.thread.timer.loop_timer_end()
                continue

            frame = None
            with self.server.thread._frame.get_frame() as fm:
                frame = fm.copy()

            self.server.thread.draw_overlay( frame )

            ret, jpg = cv2.imencode( '.jpg', frame )
            try:
                self.wfile.write( '--jpgboundary'.encode( 'utf-8' ) )
                self.send_header( 'Content-type', 'image/jpeg' )
                self.send_header( 'Content-length', '{}'.format( jpg.size ) )
                self.end_headers()
                self.wfile.write( jpg.tostring() )
                self.server.thread.timer.loop_timer_end()
            except BrokenPipeError as e:
                logger.info( 'client {} disconnected (thread {})'.format(
                    client_addr, threading.get_ident() ) )
                return
        
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

