
import os
import sys
import unittest
import time
import threading

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )

from doorbot.util import FPSTimer, RWLock, FrameLock, RWLockWriteException

class TestUtil( unittest.TestCase ):

    def setUp(self) -> None:

        return super().setUp()

    def tearDown(self) -> None:

        return super().tearDown()

    def test_fpstimer( self ):

        fps = 15
        timer = FPSTimer( self, fps=fps )
        loop_count = 10

        for i in range( loop_count ):
            timer.loop_timer_start()

            duration = timer.loop_timer_end()
            print( duration )
            self.assertGreater( duration, 0 )

        for i in range( loop_count ):
            timer.loop_timer_start()

            time.sleep( 0.5 )

            duration = timer.loop_timer_end()

            self.assertEqual( duration, 0 )

    def test_rw_lock_writing( self ):

        lock = RWLock( blocking=False )

        def read_lock():
            print( 'locking read' )
            lock._lock_read()
            time.sleep( 3 )
            print( 'unlocking read' )
            lock._release_read()

        def write_lock():
            print( 'locking write' )
            lock._lock_write()
            time.sleep( 3 )
            print( 'unlocking write' )
            lock._release_write()


        thd_1 = threading.Thread( target=read_lock )
        thd_1.daemon = True

        thd_2 = threading.Thread( target=write_lock )
        thd_2.daemon = True

        thd_1.run()
        thd_2.run()

        #lock._lock_write()

        #with self.assertRaises( RWLockWriteException ):
        #    lock._lock_read()

        #with self.assertRaises( RWLockWriteException ):
        #    lock._lock_write()

        #lock._release_write()

    def test_rw_lock_reading( self ):

        lock = RWLock()

        lock._lock_read()

        lock._lock_read()

        lock._lock_read()

        with self.assertRaises( RWLockWriteException ):
            lock._lock_write()

        lock._release_read()
        
        lock._release_read()
        
        lock._release_read()
