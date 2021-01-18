
import logging
import time
import threading
from contextlib import contextmanager

class FPSTimer( object ):

    def __init__( self, parent, **kwargs ):
        self._fps_target = float( kwargs['fps'] ) if 'fps' in kwargs else 15.0
        self._fps_target_delta = 1.0 / self._fps_target # Try fr this proc time.
        self._loop_info = threading.local()
        self.report_frames = int( kwargs['reportframes'] ) \
            if 'reportframes' in kwargs else 60
        self.parent = parent

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
                    type( self.parent ), fps_actual_delta,
                    self._fps_target_delta, threading.get_ident() ) )

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
                type( self.parent ), 1.0 / (avg_sleep + avg_work),
                threading.get_ident() ) )
            self._loop_info.durations = []

class FrameLock( object ):

    def __init__( self ):
        self._frame_ready = threading.Condition( threading.Lock() )
        self._frame_readers = 0
        self._frame = None
        self.ready = False

    @contextmanager
    def set_frame( self, frame ):
        logger = logging.getLogger( 'framelock.write' )
        self._frame_ready.acquire()
        while 0 < self._frame_readers:
            logger.debug( 'waiting for write ({} readers, thread {})...'.format(
                self._frame_readers, threading.get_ident() ) )
            self._frame_ready.wait()
        logger.debug( 'locking frame for write (thread {})...'.format(
            threading.get_ident() ) )
        self._frame = frame.copy()
        self.ready = True
        logger.debug( 'releasing write lock (thread {})'.format(
            threading.get_ident() ) )
        self._frame_ready.release()

    @contextmanager
    def get_frame( self ):
        logger = logging.getLogger( 'framelock.read' )
        logger.debug( 'locking frame for read (thread {})...'.format(
            threading.get_ident() ) )
        self._frame_ready.acquire()
        try:
            self._frame_readers += 1
        finally:
            self._frame_ready.release()
        yield self._frame
        logger.debug( 'releasing read lock (thread {})'.format(
            threading.get_ident() ) )
        self._frame_ready.acquire()
        try:
            self._frame_readers -= 1
            if not self._frame_readers:
                self._frame_ready.notifyAll()
        finally:
            self._frame_ready.release()

