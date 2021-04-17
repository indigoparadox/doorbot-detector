
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
            logger.warning(
                '%s took too long! %d seconds vs target %d (thread %d)',
                    type( self.parent ), fps_actual_delta,
                    self._fps_target_delta, threading.get_ident() )

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

            logger.info( '%s fps: %d (thread %d)',
                type( self.parent ), 1.0 / (avg_sleep + avg_work),
                threading.get_ident() )
            self._loop_info.durations = []

        return sleep_delay

# region rw_lock

class RWLockWriteException( Exception ):
    pass

class RWLock( object ):

    def __init__( self, blocking=True, lock=None ): # pylint: disable=unused-argument
        if not lock:
            lock = threading.Lock()
        self._ready = threading.Condition( lock )
        self._readers = 0
        self._wrapped_item = None
        self.logger = logging.getLogger( 'framelock' )

    @property
    def _wrapped_abstraction( self ):

        ''' This should be overwritten in derived classes if e.g. we want to
        copy the wrapped item on read for frames. '''

        return self._wrapped_item

    @_wrapped_abstraction.setter
    def _wrapped_abstraction( self, value ):

        ''' This should be overwritten in derived classes if e.g. we want to
        copy the wrapped item on write for frames. '''

        self._wrapped_item = value

    def _lock_write( self ):
        self._ready.acquire()
        while 0 < self._readers:
            self.logger.debug( 'waiting for write (%d readers, thread %d)...',
                self._readers, threading.get_ident() )
            self._ready.wait()
        self.logger.debug( 'locking frame for write (thread %d)...',
            threading.get_ident() )

    def _release_write( self ):
        self.logger.debug( 'releasing write lock (thread %d)',
            threading.get_ident() )
        self._ready.release()

    def _lock_read( self ):
        self.logger.debug( 'locking frame for read (thread %d)...',
            threading.get_ident() )

        self._ready.acquire()
        try:
            self._readers += 1
        finally:
            self._ready.release()

    def _release_read( self ):
        self.logger.debug( 'releasing read lock (thread %d)',
            threading.get_ident() )
        self._ready.acquire()
        try:
            self._readers -= 1
            if not self._readers:
                self._ready.notifyAll()
        finally:
            self._ready.release()

    @contextmanager
    def set_frame( self, frame ):
        self._lock_write()
        try:
            self._wrapped_abstraction = frame
        except Exception as exc: # pylint: disable=broad-except
            self.logger.error( '%s: %s', type( exc ), exc )
        self._release_write()

    @contextmanager
    def get_frame( self ):
        self._lock_read()
        yield self._wrapped_abstraction
        self._release_read()

class FrameLock( RWLock ):
    def __init__( self ):
        super().__init__()
        self.frame_ready = False

    @property
    def _wrapped_abstraction( self ):

        ''' This should be overwritten in derived classes if e.g. we want to
        copy the wrapped item on read for frames. '''

        return self._wrapped_item

    @_wrapped_abstraction.setter
    def _wrapped_abstraction( self, value ):

        ''' This should be overwritten in derived classes if e.g. we want to
        copy the wrapped item on write for frames. '''

        self._wrapped_item = value.copy()
        self.frame_ready = True

# endregion
