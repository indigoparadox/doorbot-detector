#!/usr/bin/env python3

import logging
import ssl
import argparse
import io
from paho.mqtt import client as mqtt_client
from configparser import ConfigParser
from tkinter import Tk, Frame, Label
from PIL import ImageTk, Image, ImageDraw
from detector.overlay import Overlays, WeatherOverlay

class SnapWindow( Frame ):

    def __init__( self, master, **kwargs ):
        super().__init__( master )
        
        logger = logging.getLogger( 'window.init' )

        self.snap_size = \
            tuple( [int( x ) for x in kwargs['snapsize'].split( ',' )] )

        self.pack()

        self.overlays = kwargs['overlays']
        self.overlays.start()

        self.overlay = kwargs['winoverlay'] if 'winoverlay' in kwargs else \
            None
        self.overlay_coords = \
            tuple( [int( x ) for x in \
                kwargs['winoverlaycoords'].split( ',' )] ) \
            if 'winoverlaycoords' in kwargs else (0, 0)

        self.image = Label( self )
        self.image.pack( fill="both", expand="yes" )
        
        self.image_pil = Image.new( 'RGB', self.snap_size )
        self.draw_image( self.image_pil )

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
        
        self.update_overlays()

    def draw_overlay( self, img ):

        if not self.overlay:
            return

        text = self.overlay.split( "\\n" )
        org = self.overlay_coords
        draw = ImageDraw.Draw( img )
        for line in text:
            line = self.overlays.line( line )
            draw.text( org, line, fill=(255, 255, 255) )
            org = (org[0], org[1] + 20)

        return img

    def draw_image( self, image ):
        image_tk = ImageTk.PhotoImage( image )
        self.image.configure( image=image_tk )
        self.image_tk = image_tk

    def update_overlays( self ):

        logger = logging.getLogger( 'window.overlays' )

        if not self.overlay:
            return

        logger.debug( 'updating...' )

        img = self.draw_overlay( self.image_pil.copy() )

        self.draw_image( img )

        self.after( 1000, self.update_overlays )

    def on_connected( self, client, userdata, flags, rc ):
        logger = logging.getLogger( 'window.connected' )
        logger.info( 'mqtt connected' )
        self.mqtt.subscribe( self.topic )
        logger.info( 'subscribed to: {}'.format( self.topic ) )

    def on_received( self, client, userdata, message ):
        logger = logging.getLogger( 'window.received' )
        logger.debug( 'snap received ({} kB)'.format( len( message.payload ) ) )
        image_raw = Image.open( io.BytesIO( message.payload ) )
        self.image_pil = image_raw.resize( self.snap_size )
        self.draw_image( self.image_pil )

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
    logger = logging.getLogger( 'main' )
    
    config = ConfigParser()
    config.read( args.config )

    root = Tk()
    root.title( 'Camera Activity' )
    root.attributes( '-topmost', True )

    overlay_thread = Overlays()

    try:
        weather_cfg = dict( config.items( 'weather' ) )
        overlay_thread.overlays.append( WeatherOverlay( **weather_cfg ) )
    except Exception as e:
        logger.error( e )

    win_cfg = dict( config.items( 'mqtt' ) )
    win_cfg['overlays'] = overlay_thread

    win = SnapWindow( root, **win_cfg )

    win.mainloop()

if '__main__' == __name__:
    main()

