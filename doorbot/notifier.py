
import logging
import threading
import time

class Notifier( object ):
    def send( self, subject, message ):
        pass

    def snapshot( self, subject, attachment ):
        pass

class LoggerNotifier( Notifier ):
    def __init__( self, **kwargs ):
        self.logger = logging.getLogger( 'detector.run.movement' )

    def send( self, subject, message ):
        if 'ignored' == subject:
            self.logger.debug( '%s: %s', subject, message )
        else:
            self.logger.info( '%s: %s', subject, message )

class MQTTNotifier( Notifier ):
    def __init__( self, **kwargs ):

        logger = logging.getLogger( 'mqtt.init' )

        from paho.mqtt import client as mqtt_client
        import ssl

        self.snapshots = True if 'snapshots' in kwargs \
            and 'true' == kwargs['snapshots'] else False
        self.snaps_retain = True if 'snapsretain' in kwargs \
            and 'true' == kwargs['snapsretain'] else False
        self.topic = kwargs['topic']
        self.mqtt = mqtt_client.Client(
            kwargs['uid'], True, None, mqtt_client.MQTTv31 )
        self.mqtt.loop_start()
        if 'logger' in kwargs and kwargs['logger'] == 'true':
            self.mqtt.enable_logger()
        if 'ssl' in kwargs and kwargs['ssl'] == 'true':
            self.mqtt.tls_set(
                kwargs['ca'], tls_version=ssl.PROTOCOL_TLSv1_2 )
        self.mqtt.on_connect = self.on_connected
        logger.info( 'connecting to MQTT at %s:%d...',
            kwargs['host'], int( kwargs['port'] ) )
        self.mqtt.connect( kwargs['host'], int( kwargs['port'] ) )

    def send( self, subject, message ):
        logger = logging.getLogger( 'mqtt.send' )
        topic = '{}/{}'.format( self.topic, subject )
        logger.debug( 'publishing %s to %s...', message, topic )
        self.mqtt.publish( topic, message )

    def snapshot( self, subject, attachment ):
        logger = logging.getLogger( 'mqtt.snapshot' )
        if not self.snapshot:
            return
        topic = '{}/{}'.format( self.topic, subject )
        sz = round( len( attachment ) / 1024, 2 )
        logger.debug( 'snapshot (%dkB) to %s...', sz, topic )
        self.mqtt.publish( topic, attachment, retain=True )
        self.mqtt.publish(
            '{}/timestamp'.format( topic ), str( time.time() ), retain=True )

    def on_connected( self, client, userdata, flags, rc ):
        logger = logging.getLogger( 'mqtt.connected' )
        logger.info( 'mqtt connected' )
        self.send( 'error', 'online' )
        self.mqtt.will_set( '{}/error'.format( self.topic ), 'died' )

    def stop( self ):
        logger = logging.getLogger( 'mqtt.stop' )
        logger.info( 'mqtt shutting down...' )
        self.mqtt.disconnect()
        self.mqtt.loop_stop()

class EMailNotifier( Notifier ):
    pass
