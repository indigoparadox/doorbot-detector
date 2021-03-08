
import threading
import logging
import os

from doorbot.exceptions import TrayNotAvailableException

INTERFACE_GTK = 1
INTERFACE_WIN32 = 2

logger = logging.getLogger( 'icon.root' )
interface = 0

try:
    import gi
    gi.require_version( 'Gtk', '3.0' )
    gi.require_version( 'AppIndicator3', '0.1' )
    from gi.repository import Gtk
    from gi.repository import AppIndicator3 as appindicator
    interface = INTERFACE_GTK
except ImportError as e:
    logger.error( 'error importing gtk: %s', e )
    try:
        from .notificationicon import NotificationIcon
        interface = INTERFACE_WIN32
    except (ImportError, ValueError) as e:
        logger.error( 'error importing win32: %s', e )
        raise TrayNotAvailableException( 'no tray icon mechanism available' ) from e

class TrayMenu( object ):
    def __init__( self ):
        self._items = {}
        if interface == INTERFACE_GTK:
            self._menu = Gtk.Menu()

        elif interface == INTERFACE_WIN32:
            self._meta = {}

        else:
            raise Exception( 'not implemented' )

    def get_checked( self, key ):
        logger = logging.getLogger( 'icon.menu.checked' )
        if key in self._items:
            if interface == INTERFACE_GTK:
                return self._items[key].get_active()
            elif interface == INTERFACE_WIN32:
                #return self._items[key][0].startswith( '+' )
                return self._meta[key]['checked']
            else:
                raise Exception( 'not implemented' )
        else:
            logger.warning(
                'tried to get status of missing option item %s', key )
            return None

    def set_checked( self, key, value ):
        logger = logging.getLogger( 'icon.menu.checked' )
        if key in self._items:
            if interface == INTERFACE_GTK:
                self._items[key].set_active( value )
            elif interface == INTERFACE_WIN32:
                #if self._items[key][0].startswith( '+' ) and not value:
                #    self._items[key] = \
                #        (self._items[key][0][1:], self._items[key][1])
                #elif value and not self._items[key][0].startswith( '+' ):
                #    self._items[key] = \
                #        ('+' + self._items[key][0], self._items[key][1])
                self._meta[key]['checked'] = value
            else:
                raise Exception( 'not implemented' )
        else:
            logger.warning(
                'tried to set status of missing option item %s', key )

    def add_item( self, key, label, callback, *args, **kwargs ):
        if interface == INTERFACE_GTK:
            self._items[key] = Gtk.MenuItem( label )
            self._items[key].connect( 'activate', callback, *args, **kwargs )
            self._menu.append( self._items[key] )
            self._items[key].show()

        elif interface == INTERFACE_WIN32:
            self._items[key] = (label, callback, key, *args)
            self._meta[key] = {}

        else:
            raise Exception( 'not implemented' )

    def add_option_item( self, key, label, checked, callback, *args, **kwargs ):
        if interface == INTERFACE_GTK:
            self._items[key] = Gtk.CheckMenuItem( label )
            self._items[key].connect( 'activate', callback, *args, **kwargs )
            self._menu.append( self._items[key] )
            self._items[key].show()
            self._items[key].set_active( checked )

        elif interface == INTERFACE_WIN32:
            self._items[key] = (self._title_checked_win32,
                self._click_checked_win32, key, callback, *args)
            self._meta[key] = {'checked': checked, 'label': label}

        else:
            raise Exception( 'not implemented' )

    def _click_checked_win32( self, *args ):
        key = args[0]

        # Toggle check.
        if self._meta[key]['checked']:
            self._meta[key]['checked'] = False
        else:
            self._meta[key]['checked'] = True

        cb_args = args[2:]
        if args[1]:
            print( args )
            args[1]( *cb_args )

    def _title_checked_win32( self, *args ):
        key = args[0]
        if self._meta[key]['checked']:
            return '+' + self._meta[key]['label']
        else:
            return self._meta[key]['label']

class TrayIcon( threading.Thread ):

    def __init__( self, iid, icon, menu, **kwargs ):
        super().__init__()

        self.logger = logging.getLogger( 'icon' )

        self.daemon = True

        icon_path = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ),
            '{}.ico'.format( icon ) )

        if interface == INTERFACE_GTK:
            category = \
                getattr( appindicator.IndicatorCategory, kwargs['category'] ) \
                if 'category' in kwargs else \
                appindicator.IndicatorCategory.APPLICATION_STATUS

            self.logger.debug( 'creating icon %s with image %s...',
                iid, icon )

            self.icon = appindicator.Indicator.new( iid, icon_path, category )
            self.icon.set_status( appindicator.IndicatorStatus.ACTIVE )

            if 'attention_icon' in kwargs:
                self.icon.set_attention_icon( kwargs['attention_icon'] )

        elif interface == INTERFACE_WIN32:
            self.ni = NotificationIcon( icon_path, iid )

        else:
            raise Exception( 'not implemented' )

        self.menu = menu

    def run( self ):

        if interface == INTERFACE_GTK:
            self.icon.set_menu( self.menu._menu )

            Gtk.main()

        elif interface == INTERFACE_WIN32:
            self.ni.items = self.menu._items.values()
            self.ni._run()

            while True:
                pass

        else:
            raise Exception( 'not implemented' )

    def stop( self ):

        if interface == INTERFACE_WIN32:
            logger.debug( 'cleaning up tray icon...' )
            self.ni.die()
