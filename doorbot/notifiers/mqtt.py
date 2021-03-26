
import ssl
import time
import logging
from urllib import parse
from urllib.parse import urlparse

from paho.mqtt import client as mqtt_client

from doorbot.notifiers import Notifier

class MQTTNotifier( Notifier ):
    def __init__( self, **kwargs ):

        super().__init__( **kwargs )

        self.logger = logging.getLogger( 'mqtt' )

        self.snapshots = True if 'snapshots' in kwargs \
            and 'true' == kwargs['snapshots'] else False
        self.snaps_retain = True if 'snapsretain' in kwargs \
            and 'true' == kwargs['snapsretain'] else False

        parsed_url = urlparse( kwargs['url'] )

        self.topic = parsed_url.path[1:] if '/' == parsed_url.path[0] \
            else parsed_url.path
        self.snapshot_topic = kwargs['snapshottopic'] \
            if 'snapshottopic' in kwargs else \
            '{}/snapshot'.format( self.topic )
        self.timestamp_topic = kwargs['timestamptopic'] \
            if 'timestamptopic' in kwargs else \
            '{}/snapshot/%m/timestamp'.format( self.topic )
        self.mqtt = mqtt_client.Client(
            kwargs['uid'], True, None, mqtt_client.MQTTv31 )
        self.mqtt.loop_start()
        if 'logger' in kwargs and kwargs['logger'] == 'true':
            self.mqtt.enable_logger()
        if 'mqtts' == parsed_url.scheme:
            self.mqtt.tls_set(
                kwargs['ca'], tls_version=ssl.PROTOCOL_TLSv1_2 )
        elif 'mqtt' != parsed_url.scheme:
            raise ValueError( 'invalid MQTT scheme specified in url' ) 
        self.mqtt.on_connect = self.on_connected
        self.logger.info( 'connecting to MQTT at %s:%d...',
            parsed_url.hostname, parsed_url.port )
        if parsed_url.username:
            self.mqtt.username_pw_set(
                parsed_url.username, parsed_url.password )
        self.mqtt.connect( parsed_url.hostname, parsed_url.port )

    @staticmethod
    def build_topic( topic, subject ):
        if r'%s' in topic:
            return topic.replace( r'%s', subject )    
        return '{}/{}'.format( topic, subject )

    def send( self, subject, message ):
        topic = MQTTNotifier.build_topic( self.topic, subject )
        self.logger.debug( 'publishing %s to %s...', message, topic )
        self.mqtt.publish( topic, message )

    def snapshot( self, subject, attachment ):
        if not self.snapshot:
            return
        snapshot_topic = \
            MQTTNotifier.build_topic( self.snapshot_topic, subject )
        timestamp_topic = \
            MQTTNotifier.build_topic( self.timestamp_topic, subject )
        sz = round( len( attachment ) / 1024, 2 )
        self.logger.debug( 'snapshot (%dkB) to %s...', sz, snapshot_topic )
        self.mqtt.publish( snapshot_topic, attachment, retain=True )
        self.mqtt.publish( timestamp_topic, str( time.time() ), retain=True )

    def on_connected( self, client, userdata, flags, rc ):
        self.logger.info( 'mqtt connected' )
        self.send( 'error', 'online' )
        self.mqtt.will_set( '{}/error'.format( self.topic ), 'died' )

    def stop( self ):
        self.logger.info( 'mqtt shutting down...' )
        self.mqtt.disconnect()
        self.mqtt.loop_stop()

PLUGIN_TYPE = 'notifiers'
PLUGIN_CLASS = MQTTNotifier
