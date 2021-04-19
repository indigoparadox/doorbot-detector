
import os
import sys
import unittest
import logging
from contextlib import ExitStack
from unittest.mock import patch, Mock, call

from faker import Faker

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )

import doorbot.notifiers.logger
from doorbot.notifiers.email import EMailNotifier
from doorbot.portability import image_to_jpeg
from fake_camera import FakeCamera

class TestNotifier( unittest.TestCase ):

    def setUp( self ):
        self.fake = Faker()
        self.fake.add_provider( FakeCamera )
        self.logger = logging.getLogger( 'test' )

    def test_notify_email( self ):
        pass

    def test_notify_mqtt_build_topic( self ):

        import doorbot.notifiers.mqtt

        subject = 'movement'
        topics = {
            r'dev/doorbot/detector':
                'dev/doorbot/detector/movement',
            r'dev/doorbot/detector/snapshot':
                'dev/doorbot/detector/snapshot/movement',
            r'dev/doorbot/detector/snapshot/%s/timestamp':
                'dev/doorbot/detector/snapshot/movement/timestamp',
            r'doorbot/detector':
                'doorbot/detector/movement',
            r'doorbot/detector/snapshot':
                'doorbot/detector/snapshot/movement',
            r'doorbot/detector/snapshot/%s/timestamp':
                'doorbot/detector/snapshot/movement/timestamp',
            r'doorbot/detector/%s/timestamp':
                'doorbot/detector/movement/timestamp',
        }

        for topic, res in topics.items():
            self.assertEqual( 
                doorbot.notifiers.mqtt.MQTTNotifier.build_topic(
                    topic, subject ),
                res )

    def test_notify_mqtt( self ):

        with ExitStack() as mock_stack:
            mock_mqtt = mock_stack.enter_context(
                patch( 'paho.mqtt.client', create=True ) )
            mock_time = mock_stack.enter_context(
                patch( 'time.time', create=True ) )
            import doorbot.notifiers.mqtt

            mock_instance = mock_mqtt.Client.return_value
            mock_time.return_value = 1024.1028

            frame = self.fake.random_image( 320, 240 ) # pylint: disable=no-member
            frame_jpg = image_to_jpeg( frame )

            notifier = doorbot.notifiers.mqtt.MQTTNotifier(
                'test_notifier',
                camera='test',
                uid='testuid',
                url='mqtt://localhost:1883/testtopic',
                snapshottopic='testtopic/snapshot',
                timestamptopic='testtopic/snapshot/timestamp' )

            notifier.send( 'Test Subject', 'Test Message' )
            notifier.snapshot( 'Test Snapshot', frame_jpg )

            mock_mqtt.Client.assert_called_once_with(
                'testuid', True, None,  mock_mqtt.MQTTv31 )
            mock_instance.connect.assert_called_once_with(
                 'localhost', 1883 )
            mock_instance.publish.assert_has_calls( [
                call( 'testtopic/Test Subject', 'Test Message' ),
                call( 'testtopic/snapshot/Test Snapshot', frame_jpg, retain=True ),
                call( 'testtopic/snapshot/timestamp/Test Snapshot',
                    str( 1024.1028 ), retain=True )
            ] )

    def test_notify_logger( self ):

        mock_log = Mock()

        doorbot.notifiers.logger.logging = mock_log

        args = {
            'enable': 'true',
            'camera': 'test'
        }

        notifier = doorbot.notifiers.logger.LoggerNotifier( 'test_notifier', **args )
        notifier.send( 'Test', 'Test Notify' )

        logger = mock_log.getLogger.return_value
        logger.info.assert_called_once_with( '%s: %s', 'Test', 'Test Notify' )
