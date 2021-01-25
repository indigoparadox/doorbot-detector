
import threading
import logging

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
except Exception as e:
    logger.error( 'error importing gtk: {}'.format( e ) )

class TrayMenu( object ):
    def __init__( self ):
        self.items = {}
        if INTERFACE_GTK:
            self._menu = Gtk.Menu()
        else:
            raise Exception( 'not implemented' )

    def get_checked( self, key ):
        logger = logging.getLogger( 'icon.menu.checked' )
        if key in self.items:
            return self.items[key].get_active()
        else:
            logger.warning(
                'tried to get status of missing option item {}'.format( key ) )
            return None

    def set_checked( self, key, value ):
        logger = logging.getLogger( 'icon.menu.checked' )
        if key in self.items:
            self.items[key].set_active( value )
        else:
            logger.warning(
                'tried to set status of missing option item {}'.format( key ) )

    def add_item( self, key, label, callback, *args, **kwargs ):
        if INTERFACE_GTK:
            self.items[key] = Gtk.MenuItem( label ) 
            self.items[key].connect( 'activate', callback, *args, **kwargs )
            self._menu.append( self.items[key] )
            self.items[key].show()
        else:
            raise Exception( 'not implemented' )

    def add_option_item( self, key, label, checked, callback, *args, **kwargs ):
        if INTERFACE_GTK:
            self.items[key] = Gtk.CheckMenuItem( label ) 
            self.items[key].connect( 'activate', callback, *args, **kwargs )
            self._menu.append( self.items[key] )
            self.items[key].show()
            self.items[key].set_active( checked )
        else:
            raise Exception( 'not implemented' )

class TrayIcon( threading.Thread ):

    def __init__( self, iid, icon, menu, **kwargs ):
        super().__init__()

        logger = logging.getLogger( 'icon.init' )

        self.daemon = True

        if INTERFACE_GTK:
            category = \
                getattr( appindicator.IndicatorCategory, kwargs['category'] ) \
                if 'category' in kwargs else \
                appindicator.IndicatorCategory.APPLICATION_STATUS

            logger.debug( 'creating icon {} with image {}...'.format(
                iid, icon ) )

            self.icon = appindicator.Indicator.new( iid, icon, category )
            self.icon.set_status( appindicator.IndicatorStatus.ACTIVE )

            if 'attention_icon' in kwargs:
                self.icon.set_attention_icon( kwargs['attention_icon'] )
        else:
            raise Exception( 'not implemented' )

        self.menu = menu

    def run( self ):

        if INTERFACE_GTK:
            self.icon.set_menu( self.menu._menu )

            Gtk.main()
        else:
            raise Exception( 'not implemented' )

