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

    def __init__( self, master, topic, ca, host, port, uid, use_ssl, snapsz ):
        super().__init__( master )
        
        logger = logging.getLogger( 'window.init' )

        self.snap_size = snapsz

        self.pack()

        img = Image.new( 'RGB', self.snap_size )
        self.image_tk = ImageTk.PhotoImage( img )

        self.image = Label( self, image=self.image_tk )
        self.image.pack( fill="both", expand="yes" )
        
        self.mqtt = mqtt_client.Client( uid, True, None, mqtt_client.MQTTv31 )
        self.mqtt.loop_start()
        self.mqtt.enable_logger()
        self.topic = topic
        self.mqtt.message_callback_add( topic, self.on_received )
        if use_ssl:
            self.mqtt.tls_set( ca, tls_version=ssl.PROTOCOL_TLSv1_2 )
        self.mqtt.on_connect = self.on_connected
        logger.info( 'connecting to MQTT at {}:{}...'.format( host, port ) )
        self.mqtt.connect( host, port )

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
    #root.lift()
    root.attributes( '-topmost', True )

    snapsize = \
        tuple( [int( x ) for x in config['mqtt']['snapsize'].split( ',' )] )

    win = SnapWindow(
        root,
        config['mqtt']['topic'] + '/snapshot/movement',
        config['mqtt']['ca'],
        config['mqtt']['host'],
        config.getint( 'mqtt', 'port' ),
        'window-' + config['mqtt']['uid'],
        True if 'true' == config['mqtt']['ssl'] else False,
        snapsize )

    win.mainloop()

if '__main__' == __name__:
    main()

