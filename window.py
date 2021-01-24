#!/usr/bin/env python3

import logging
import ssl
import argparse
import io
from paho.mqtt import client as mqtt_client
from configparser import ConfigParser
from tkinter import Tk, Frame, Label
from PIL import ImageTk, Image

class SnapWindow( Frame ):

    def __init__( self, master, **kwargs ):
        super().__init__( master )
        
        logger = logging.getLogger( 'window.init' )

        self.snap_size = \
            tuple( [int( x ) for x in kwargs['snapsize'].split( ',' )] )

        self.pack()

        img = Image.new( 'RGB', self.snap_size )
        self.image_tk = ImageTk.PhotoImage( img )

        self.image = Label( self, image=self.image_tk )
        self.image.pack( fill="both", expand="yes" )
        
        self.mqtt = mqtt_client.Client(
            'window-{}'.format( kwargs['uid'] ),
            True, None, mqtt_client.MQTTv31 )
        self.mqtt.loop_start()
        self.mqtt.enable_logger()
        self.topic = '{}/snapshot/movement'.format( kwargs['topic'] )
        self.mqtt.message_callback_add( self.topic, self.on_received )
        if 'ssl' in kwargs and 'true' == kwargs['ssl']:
            self.mqtt.tls_set( kwargs['ca'], tls_version=ssl.PROTOCOL_TLSv1_2 )
        self.mqtt.on_connect = self.on_connected
        host_port = (kwargs['host'], int( kwargs['port'] ))
        logger.info( 'connecting to MQTT at {}...'.format( host_port ) )
        self.mqtt.connect( host_port[0], host_port[1] )

    def on_connected( self, client, userdata, flags, rc ):
        logger = logging.getLogger( 'window.connected' )
        logger.info( 'mqtt connected' )
        self.mqtt.subscribe( self.topic )
        logger.info( 'subscribed to: {}'.format( self.topic ) )

    def on_received( self, client, userdata, message ):
        logger = logging.getLogger( 'window.received' )
        logger.debug( 'snap received ({} kB)'.format( len( message.payload ) ) )
        img = Image.open( io.BytesIO( message.payload ) )
        img = img.resize( self.snap_size )
        image_tk = ImageTk.PhotoImage( img )
        self.image.configure( image=image_tk )
        self.image_tk = image_tk

    def stop( self ):
        logger = logging.getLogger( 'window.stop' )
        logger.info( 'mqtt shutting down...' )
        self.mqtt.disconnect()
        self.mqtt.loop_stop()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument( '-c', '--config', action='store' )
    parser.add_argument( '-v', '--verbose', action='store_true' )
    args = parser.parse_args()

    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    logging.basicConfig( level=level )
    
    config = ConfigParser()
    config.read( args.config )

    root = Tk()
    root.title( 'Camera Activity' )
    root.attributes( '-topmost', True )

    win_cfg = dict( config.items( 'mqtt' ) )

    win = SnapWindow( root, **win_cfg )

    win.mainloop()

if '__main__' == __name__:
    main()

