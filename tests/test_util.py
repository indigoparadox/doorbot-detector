
import os
import sys
import unittest
import time
import threading
import logging

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )

from doorbot.util import FPSTimer, RWLock, FrameLock, RWLockWriteException

class TestUtil( unittest.TestCase ):

    def setUp(self) -> None:

        logging.basicConfig( level=logging.ERROR )
        self.logger = logging.getLogger( 'test_lock' )
        self.logger.setLevel( logging.DEBUG )
        self.lock_obj = threading.Lock()
        self.lock = RWLock( blocking=False, lock=self.lock_obj )

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

        finished = threading.Barrier( 4, timeout=10 )
        write_lock_test_stg_1 = threading.Barrier( 3, timeout=5 )

        def write_lock_a():
            self.assertFalse( self.lock_obj.locked() )
            self.assertEqual( self.lock._readers, 0 )
            self.lock._lock_write()
            self.logger.debug( 'engaged first write lock' )
            self.assertTrue( self.lock_obj.locked() )
            self.assertEqual( self.lock._readers, 0 )

            # Notify other threads to test.
            write_lock_test_stg_1.wait()

            # Wait for other threads to test.
            time.sleep( 3 )

            self.lock._release_write()
            self.logger.debug( 'released first write lock' )
            finished.wait()

        def write_lock_b():
            # Wait until write lock test has started
            write_lock_test_stg_1.wait()
            self.assertTrue( self.lock_obj.locked() )
            self.logger.debug( 'second write lock waiting for first write lock' )
            self.lock._lock_write()

            self.logger.debug( 'engaged second write lock' )
            self.assertTrue( self.lock_obj.locked() )

            self.lock._release_write()
            self.logger.debug( 'released second write lock' )
            finished.wait()

        def read_lock():
            # Wait until write lock test has started
            write_lock_test_stg_1.wait()
            self.assertEqual( self.lock._readers, 0 )
            self.logger.debug( 'first read lock waiting for first write lock' )
            self.lock._lock_read()
            self.logger.debug( 'engaged first read lock' )
            self.assertFalse( self.lock_obj.locked() )
            self.assertGreater( self.lock._readers, 0 )
            self.lock._release_read()
            self.logger.debug( 'released first read lock' )
            self.assertEqual( self.lock._readers, 0 )
            finished.wait()

        thd_1 = threading.Thread( target=write_lock_a )
        thd_1.daemon = True

        thd_2 = threading.Thread( target=read_lock )
        thd_2.daemon = True

        thd_3 = threading.Thread( target=write_lock_b )
        thd_3.daemon = True

        thd_1.start()
        thd_2.start()
        thd_3.start()

        finished.wait()

    def test_rw_lock_reading( self ):

        finished = threading.Barrier( 4, timeout=10 )
        write_lock_test_stg_1 = threading.Barrier( 3, timeout=5 )

        def read_lock_a():
            # Wait until write lock test has started
            self.assertEqual( self.lock._readers, 0 )
            self.lock._lock_read()
            self.logger.debug( 'engaged first read lock' )
            self.assertFalse( self.lock_obj.locked() )
            self.assertGreater( self.lock._readers, 0 )

            # Notify other threads to test.
            write_lock_test_stg_1.wait()

            # Wait for other threads to test.
            time.sleep( 3 )

            self.lock._release_read()
            self.logger.debug( 'released first read lock' )
            self.assertEqual( self.lock._readers, 0 )
            finished.wait()

        def read_lock_b():
            # Wait until write lock test has started
            write_lock_test_stg_1.wait()
            self.assertEqual( self.lock._readers, 1 )
            self.logger.debug( 'second read lock waiting for first write lock' )
            self.lock._lock_read()
            self.logger.debug( 'enaged second read lock' )
            self.assertFalse( self.lock_obj.locked() )
            self.assertGreater( self.lock._readers, 1 )
            self.lock._release_read()
            self.logger.debug( 'released second read lock' )
            self.assertEqual( self.lock._readers, 1 )
            finished.wait()
    
        def write_lock():
            # Wait until write lock test has started
            write_lock_test_stg_1.wait()
            self.assertFalse( self.lock_obj.locked() )
            self.logger.debug( 'first write lock waiting for first read lock' )
            self.lock._lock_write()

            self.logger.debug( 'engaged first write lock' )
            self.assertTrue( self.lock_obj.locked() )

            self.lock._release_write()
            self.logger.debug( 'released first write lock' )
            finished.wait()

        thd_1 = threading.Thread( target=read_lock_a )
        thd_1.daemon = True

        thd_2 = threading.Thread( target=read_lock_b )
        thd_2.daemon = True

        thd_3 = threading.Thread( target=write_lock )
        thd_3.daemon = True

        thd_1.start()
        thd_2.start()
        thd_3.start()

        finished.wait()
