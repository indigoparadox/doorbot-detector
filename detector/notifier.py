
import logging

class Notifier( object ):
    def send( self, subject, message ):
        pass

class LoggerNotifier( Notifier ):
    def __init__( self, **kwargs ):
        self.logger = logging.getLogger( 'detector.run.movement' )

    def send( self, subject, message ):
        if 'ignored' == subject:
            self.logger.debug( '{}: {}'.format( subject, message ) )
        else:
            self.logger.info( '{}: {}'.format( subject, message ) )

class MQTTNotifier( Notifier ):
    def __init__( self, **kwargs ):

        logger = logging.getLogger( 'mqtt.init' )

        from paho.mqtt import client as mqtt_client
        import ssl

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
        logger.info( 'connecting to MQTT at {}:{}...'.format(
            kwargs['host'], int( kwargs['port'] ) ) )
        self.mqtt.connect( kwargs['host'], int( kwargs['port'] ) )

    def send( self, subject, message ):
        self.mqtt.publish( '{}/{}'.format( self.topic, subject ), message )

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

