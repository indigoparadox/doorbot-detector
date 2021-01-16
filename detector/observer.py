
import logging
import time
import cv2
import threading
from socketserver import ThreadingMixIn
from http.server import BaseHTTPRequestHandler, HTTPServer

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
        self._fps_target = int( kwargs['fps'] ) if 'fps' in kwargs else 15
        self._fps_target_delta = 1.0 / self._fps_target # Try fr this proc time.
        self._loop_info = threading.local()
        self.report_frames = int( kwargs['reportframes'] ) \
            if 'reportframes' in kwargs else 60

    def loop_timer_start( self ):
        self._loop_info.tmr_start = time.time()

    def loop_timer_end( self ):
        logger = logging.getLogger( 'observer.timer' )
        loop_end = time.time()
        fps_actual_delta = loop_end - self._loop_info.tmr_start

        sleep_delay = 0
        if fps_actual_delta < self._fps_target_delta:
            # We've hit our target delta, so sleep the difference off.
            sleep_delay = self._fps_target_delta - fps_actual_delta
            time.sleep( sleep_delay )
        else:
            logger.warn(
                '{} took too long! {} seconds vs target {} (thread {})'.format(
                    type( self ), fps_actual_delta, self._fps_target_delta,
                    threading.get_ident() ) )

        # Store duration in local loop data list, creating it if not existant
        # for this thread.
        try:
            self._loop_info.durations.append( (fps_actual_delta, sleep_delay) )
        except AttributeError:
            self._loop_info.durations = []
            self._loop_info.durations.append( (fps_actual_delta, sleep_delay) )

        if len( self._loop_info.durations ) > self.report_frames:
            # Sleep time + work time = total loop time.
            avg_sleep = sum( x[1] for x in self._loop_info.durations ) / \
                len( self._loop_info.durations )
            avg_work = sum( x[0] for x in self._loop_info.durations ) / \
                len( self._loop_info.durations )

            logger.debug( '{} fps: {} (thread {})'.format(
                type( self ), 1.0 / (avg_sleep + avg_work),
                threading.get_ident() ) )
            self._loop_info.durations = []

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
            self.loop_timer_start()
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
            self.loop_timer_end()

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
            self.server.thread.loop_timer_start()
            jpg = None
            try:
                ret, jpg = cv2.imencode( '.jpg', self.server.thread.frame )
            except Exception as e:
                logger.warning( 'encoder error: {} (thread {})'.format(
                    e, threading.get_ident() )
                time.sleep( 1 )
                continue
            self.wfile.write( '--jpgboundary'.encode( 'utf-8' ) )
            self.send_header( 'Content-type', 'image/jpeg' )
            self.send_header( 'Content-length', '{}'.format( jpg.size ) )
            self.end_headers()
            self.wfile.write( jpg.tostring() )
            self.server.thread.loop_timer_end()
        
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

