#!/usr/bin/env python3

import logging
import ssl
import argparse
import io
from datetime import datetime
from configparser import ConfigParser
from tkinter import TclError, Tk, Frame, Label

from paho.mqtt import client as mqtt_client
from PIL import ImageTk, Image, ImageDraw

TrayMenu = None
TrayIcon = None
from doorbot.exceptions import TrayNotAvailableException
try:
    from doorbot.peephole.icon import TrayIcon, TrayMenu
except TrayNotAvailableException as exc:
    print( exc )

class SnapWindow( Frame ):

    def __init__( self, master, **kwargs ):
        super().__init__( master )

        self.logger = logging.getLogger( 'peephole' )

        self.snap_size = \
            tuple( [int( x ) for x in kwargs['snapsize'].split( ',' )] )

        # Setup tray icon.
        self.icon = kwargs['icon'] if 'icon' in kwargs else None
        if self.icon:
            self.icon.menu.add_option_item(
                'autohide', 'Auto-Hide on Idle', False,
                self.toggle_autohide )
            self.icon.menu.add_item( 'exit', 'Exit', self.stop )

            # Setup autohide only if icon is available.
            self.autohide_delay = int( kwargs['winautohidedelay'] ) if \
                'winautohidedelay' in kwargs else 1000
            self._autohide = True if 'winautohide' in kwargs and \
                'true' == kwargs['winautohide'] else False
        else:
            self._autohide = False
        self.autohide_after = None

        # Setup always-on-top.
        self.always_on_top = False if 'winalwaysontop' in kwargs and \
            'true' != kwargs['winalwaysontop'] else True

        self.pack()

        # Setup image drawing area.
        self.image = Label( self )
        self.image.pack( fill="both", expand="yes" )

        self.image_pil = Image.new( 'RGB', self.snap_size )
        self.draw_image( self.image_pil )

        # Setup MQTT.
        self.mqtt = mqtt_client.Client(
            'window-{}'.format( kwargs['uid'] ),
            True, None, mqtt_client.MQTTv31 )
        self.mqtt.loop_start()
        self.mqtt.enable_logger()
        self.topic = '{}/snapshot/movement'.format( kwargs['topic'] )
        self.mqtt.message_callback_add( self.topic, self.on_snap_received )
        if 'ssl' in kwargs and 'true' == kwargs['ssl']:
            self.mqtt.tls_set( kwargs['ca'], tls_version=ssl.PROTOCOL_TLSv1_2 )
        self.mqtt.on_connect = self.on_connected
        host_port = (kwargs['host'], int( kwargs['port'] ))
        self.logger.info( 'connecting to MQTT at %s...', host_port )
        self.mqtt.connect( host_port[0], host_port[1] )

        if self._autohide:
            self.logger.debug( 'autohide enabled' )
            self.after( self.autohide_delay, self.hide_window )

    @property
    def autohide( self ):
        return self.icon.menu.get_checked( 'autohide' )

    @autohide.setter
    def autohide( self, value ):
        self.icon.menu.set_checked( 'autohide', value )

    def get_attention( self ):
        if self.always_on_top:
            self.master.attributes( '-topmost', True )

    def hide_window( self ):
        self.logger.debug( 'hiding window...' )
        self.master.withdraw()

    def show_window( self ):
        self.logger.debug( 'canceling hide' )
        self.master.deiconify()

    def draw_image( self, image ):

        image_tk = ImageTk.PhotoImage( image )
        self.image.configure( image=image_tk )
        self.image_tk = image_tk

    def toggle_autohide( self, *args, **kwargs ):
        self.logger.debug( 'clicked' )

        if not self._autohide and self.autohide_after:
            self.after_cancel( self.autohide_after )
            self.autohide_after = None
            self.show_window()
        elif self._autohide:
            self.logger.debug( 'waiting 1 second to hide...' )
            self.autohide_after = self.after(
                self.autohide_delay, self.hide_window )

    def on_connected( self, client, userdata, flags, rc ):
        self.logger.info( 'mqtt connected' )
        self.mqtt.subscribe( self.topic )
        self.mqtt.subscribe( self.topic + '/timestamp' )
        self.logger.info( 'subscribed to: %s', self.topic )

    def on_snap_received( self, client, userdata, message ):

        if self._autohide and self.autohide_after:
            self.logger.debug( 'canceling hide' )
            self.after_cancel( self.autohide_after )
            self.autohide_after = None

        # Show the window no matter what.
        self.show_window()

        self.get_attention()

        self.logger.debug( 'snap received (%d kB)', len( message.payload ) )
        image_raw = Image.open( io.BytesIO( message.payload ) )
        self.image_pil = image_raw.resize( self.snap_size )
        img = self.image_pil.copy()
        self.draw_image( img )

        if self._autohide:
            self.logger.debug( 'waiting 1 second to hide...' )
            self.autohide_after = self.after(
                self.autohide_delay, self.hide_window )

    def stop( self, *args, **kwargs ):
        self.logger.info( 'mqtt shutting down...' )
        self.mqtt.disconnect()
        self.mqtt.loop_stop()
        if self.icon:
            self.icon.stop()
        try:
            self.master.destroy()
        except TclError as e:
            self.logger.error( 'error stopping tk: %s', e )

    def mainloop( self ):
        super().mainloop()

win = None

def main():

    global win

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

    tray_menu = None
    tray_icon = None
    if TrayMenu:
        tray_menu = TrayMenu()
        tray_icon = \
            TrayIcon( 'detector-window-icon', 'camera-web', tray_menu )

    win_cfg = dict( config.items( 'doorbot.notifiers.mqtt' ) )
    win_cfg['icon'] = tray_icon

    win = SnapWindow( root, **win_cfg )
    if tray_icon:
        tray_icon.start()

    win.mainloop()

    win.stop()

if '__main__' == __name__:
    try:
        main()
    except KeyboardInterrupt as e:
        #logger.info( 'quitting on ctrl-c' )
        win.stop()
