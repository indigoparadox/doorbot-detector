#!/usr/bin/env python3

import logging
import ssl
import argparse
import io
from paho.mqtt import client as mqtt_client
from configparser import ConfigParser
from tkinter import Tk, Frame, Label
from PIL import ImageTk, Image, ImageDraw
from detector.overlay import Overlays, WeatherOverlay, OverlayHandler
from detector.icon import TrayIcon, TrayMenu
from datetime import datetime

class SnapWindow( Frame ):

    def __init__( self, master, **kwargs ):
        super().__init__( master )
        
        logger = logging.getLogger( 'window.init' )

        #self.master = master

        self.snap_size = \
            tuple( [int( x ) for x in kwargs['snapsize'].split( ',' )] )

        self.icon = kwargs['icon']
        self.icon.menu.add_option_item( 
            'autohide', 'Auto-Hide on Idle', False,
            self.toggle_autohide )

        self.autohide = True if 'winautohide' in kwargs and \
            'true' == kwargs['winautohide'] else False
        self.autohide_after = None
        self.autohide_delay = int( kwargs['winautohidedelay'] ) if \
            'winautohidedelay' in kwargs else 1000

        self.pack()

        self.timestamp_overlay = kwargs['timestamp_overlay']

        self.overlays = kwargs['overlays']
        self.overlay_refresh_delay = int( kwargs['overlayrefreshdelay'] ) if \
            'overlayrefreshdelay' in kwargs else 1000
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
        self.mqtt.message_callback_add( self.topic, self.on_snap_received )
        self.mqtt.message_callback_add(
            self.topic + '/timestamp', self.on_ts_received )
        if 'ssl' in kwargs and 'true' == kwargs['ssl']:
            self.mqtt.tls_set( kwargs['ca'], tls_version=ssl.PROTOCOL_TLSv1_2 )
        self.mqtt.on_connect = self.on_connected
        host_port = (kwargs['host'], int( kwargs['port'] ))
        logger.info( 'connecting to MQTT at {}...'.format( host_port ) )
        self.mqtt.connect( host_port[0], host_port[1] )
        
        self.update_overlays()

        if self.autohide:
            logger.debug( 'autohide enabled' )
            self.after( self.autohide_delay, self.hide_window )

    @property
    def autohide( self ):
        return self.icon.menu.get_checked( 'autohide' )

    @autohide.setter
    def autohide( self, value ):
        self.icon.menu.set_checked( 'autohide', value )

    def draw_overlay( self, img ):

        if not self.overlay:
            return

        text = self.overlay.split( "\\n" )
        org = self.overlay_coords
        draw = ImageDraw.Draw( img )
        outline_color = (0, 0, 0)
        fill_color = (255, 255, 255)

        for line in text:
            line = self.overlays.line( line )

            # Draw outline.
            x = org[0]
            y = org[1]
            draw.text( (x-1, y), line, fill=outline_color )
            draw.text( (x+1, y), line, fill=outline_color )
            draw.text( (x, y - 1), line, fill=outline_color )
            draw.text( (x, y + 1), line, fill=outline_color )

            # Draw text.
            draw.text( org, line, fill=fill_color )

            org = (org[0], org[1] + 10)

        return img

    def hide_window( self ):
        logger = logging.getLogger( 'window.hide' )
        logger.debug( 'hiding window...' )
        self.master.withdraw()

    def show_window( self ):
        logger = logging.getLogger( 'window.hide' )
        logger.debug( 'canceling hide' )
        self.master.deiconify()

    def draw_image( self, image ):
        
        logger = logging.getLogger( 'window.image.draw' )

        image_tk = ImageTk.PhotoImage( image )
        self.image.configure( image=image_tk )
        self.image_tk = image_tk

    def toggle_autohide( self, w ):
        logger = logging.getLogger( 'window.icon' )
        logger.debug( 'clicked' )

        if not self.autohide and self.autohide_after:
            self.after_cancel( self.autohide_after )
            self.autohide_after = None
            self.show_window()
        elif self.autohide:
            logger.debug( 'waiting 1 second to hide...' )
            self.autohide_after = self.after(
                self.autohide_delay, self.hide_window )

    def update_overlays( self ):

        logger = logging.getLogger( 'window.overlays' )

        if not self.overlay:
            return

        #logger.debug( 'updating...' )

        img = self.draw_overlay( self.image_pil.copy() )

        self.draw_image( img )

        self.after( self.overlay_refresh_delay, self.update_overlays )

    def on_connected( self, client, userdata, flags, rc ):
        logger = logging.getLogger( 'window.connected' )
        logger.info( 'mqtt connected' )
        self.mqtt.subscribe( self.topic )
        self.mqtt.subscribe( self.topic + '/timestamp' )
        logger.info( 'subscribed to: {}'.format( self.topic ) )

    def on_snap_received( self, client, userdata, message ):
        logger = logging.getLogger( 'window.received' )

        if self.autohide and self.autohide_after:
            logger.debug( 'canceling hide' )
            self.after_cancel( self.autohide_after )
            self.autohide_after = None

        # Show the window no matter what.
        self.show_window()

        logger.debug( 'snap received ({} kB)'.format( len( message.payload ) ) )
        image_raw = Image.open( io.BytesIO( message.payload ) )
        self.image_pil = image_raw.resize( self.snap_size )
        img = self.draw_overlay( self.image_pil.copy() )
        self.draw_image( img )

        if self.autohide:
            logger.debug( 'waiting 1 second to hide...' )
            self.autohide_after = self.after(
                self.autohide_delay, self.hide_window )

    def on_ts_received( self, client, userdata, message ):
        msg_str = message.payload.decode( 'utf-8' )
        ts = datetime.fromtimestamp( float( msg_str ) )
        self.timestamp_overlay.current = \
            'updated {}'.format( ts.strftime( '%I:%M:%S %p %m/%d/%Y' ) )
        logger.debug( 'timestamp: {}'.format( self.timestamp_overlay.current ) )

    def stop( self ):
        logger = logging.getLogger( 'window.stop' )
        logger.info( 'mqtt shutting down...' )
        self.mqtt.disconnect()
        self.mqtt.loop_stop()

    def mainloop( self ):
        super().mainloop()


class TimestampOverlay( OverlayHandler ):

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )
        self.token = '<timestamp>'

def main():

    global logger

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-c', '--config', action='store', default='detector.ini' )
    parser.add_argument( '-v', '--verbose', action='store_true' )
    args = parser.parse_args()

    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    logging.basicConfig( level=level )
    logging.getLogger( 'PIL.PngImagePlugin' ).setLevel( logging.WARNING )
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

    tso = TimestampOverlay()
    overlay_thread.overlays.append( tso )

    tray_menu = TrayMenu()
    tray_icon = \
        TrayIcon( 'detector-window-icon', 'camera-web', tray_menu )

    win_cfg = dict( config.items( 'mqtt' ) )
    win_cfg['overlays'] = overlay_thread
    win_cfg['timestamp_overlay'] = tso
    win_cfg['icon'] = tray_icon

    win = SnapWindow( root, **win_cfg )
    tray_icon.start()

    win.mainloop()

if '__main__' == __name__:
    try:
        main()
    except KeyboardInterrupt as e:
        logger.info( 'quitting on ctrl-c' )

