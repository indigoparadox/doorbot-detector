
import os
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch, Mock, call

from faker import Faker

sys.path.insert( 0, os.path.dirname( os.path.dirname( __file__) ) )

import doorbot.notifiers.mqtt
from doorbot.notifiers.email import EMailNotifier
from doorbot.notifiers.logger import LoggerNotifier
from doorbot.portability import image_to_jpeg
from fake_camera import FakeCamera

class TestNotifier( unittest.TestCase ):

    def setUp( self ):
        self.fake = Faker()
        self.fake.add_provider( FakeCamera )

    def test_notify_email( self ):
        pass

    def test_notify_mqtt( self ):

        with ExitStack() as mock_stack:
            mock_mqtt = mock_stack.enter_context(
                patch( 'paho.mqtt.client', autospec=True ) )
            mock_time = mock_stack.enter_context(
                patch( 'time.time', autospec=True ) )
            doorbot.notifiers.mqtt.mqtt_client = mock_mqtt
            doorbot.notifiers.mqtt.time.time = mock_time
            mock_instance = mock_mqtt.Client.return_value
            mock_time.return_value = 1024.1028

            frame = self.fake.random_image( 320, 240 )
            frame_jpg = image_to_jpeg( frame )

            notifier = doorbot.notifiers.mqtt.MQTTNotifier(
                topic='testtopic', uid='testuid', host='localhost', port=1883 )

            notifier.send( 'Test Subject', 'Test Message' )
            notifier.snapshot( 'Test Snapshot', frame_jpg )

            mock_mqtt.Client.assert_called_once_with(
                'testuid', True, None,  mock_mqtt.MQTTv31 )
            mock_instance.connect.assert_called_once_with(
                 'localhost', 1883 )
            mock_instance.publish.assert_has_calls( [
                call( 'testtopic/Test Subject', 'Test Message' ),
                call( 'testtopic/Test Snapshot', frame_jpg, retain=True ),
                call( 'testtopic/Test Snapshot/timestamp',
                    str( 1024.1028 ), retain=True )
            ] )