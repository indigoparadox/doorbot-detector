
import os
import sys
import unittest
import random

from faker import Faker

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )

from tests.fake_camera import FakeCamera
from doorbot.detector import DetectionEvent, MotionDetector

class TestDetector( unittest.TestCase ):

    def setUp(self) -> None:

        self.fake = Faker()
        self.fake.add_provider( FakeCamera )

        self.motion_detector_config = {
            'threshold': '50',
            'varthreshold': '200',
            'blur': '5',
            'minw': '20',
            'minh': '20',
            'fps': '5.0',
            'width': '640',
            'height': '480',
            'ignoreedges': 'false' }

        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_handle_motion( self ):

        detector = MotionDetector( **self.motion_detector_config )
        dimensions = [
            int( self.motion_detector_config['width'] ),
            int( self.motion_detector_config['height'] )]
        image = self.fake.random_image( *dimensions )

        for i in range( 20 ):
            rect = self.fake.frame_rect( self.motion_detector_config )
            event = detector.handle_movement( image, *rect )

            self.assertTrue( isinstance( event, DetectionEvent ) )
            self.assertEqual( event.dimensions, tuple( rect[2:] ) )
            self.assertEqual( event.position, tuple( rect[:2] ) )
            self.assertEqual( event.event_type, 'movement' )

    def test_detect_motion( self ):

        detector = MotionDetector( **self.motion_detector_config )

        for i in range( 20 ):
            dimensions = [
                int( self.motion_detector_config['width'] ),
                int( self.motion_detector_config['height'] )]
            image = self.fake.random_image( *dimensions )
            event = detector.detect( image )

            self.assertTrue( isinstance( event, DetectionEvent ) )
            self.assertEqual( event.event_type, 'movement' )
            self.assertIs( event.frame, image )

    def test_detect_no_motion( self ):

        detector = MotionDetector( **self.motion_detector_config )

        dimensions = [
            int( self.motion_detector_config['width'] ),
            int( self.motion_detector_config['height'] )]
        image = self.fake.random_image( *dimensions )

        # Detect once to set the baseline.
        detector.detect( image )

        for i in range( 20 ):
            event = detector.detect( image )

            self.assertIsNone( event )
