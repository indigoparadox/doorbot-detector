
        
from doorbot.cameras.rtsp import PLUGIN_CLASS, PLUGIN_TYPE
import time

from doorbot.overlays import OverlayHandler

class TimeOverlay( OverlayHandler ):

    @property
    def tokens( self ):
        return {'time': time.strftime( '%H:%M:%S %m/%d/%Y' )}

PLUGIN_TYPE = 'overlays'
PLUGIN_CLASS = TimeOverlay
