
from doorbot.cameras.rtsp import PLUGIN_CLASS, PLUGIN_TYPE
import html
import logging
import time

import requests
from requests.exceptions import RequestException

from doorbot.overlays import OverlayHandler

class WeatherOverlay( OverlayHandler ):

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )
        self.logger = logging.getLogger( 'overlay.weather' )
        self.url = kwargs['url']
        self.refresh = float( kwargs['refresh'] ) if 'refresh' in kwargs else \
            300
        self.last_updated = time.time()
        self.countdown = 0
        self.format = kwargs['format'] if 'format' in kwargs else '<outTemp>'
        self.current = ''

    @property
    def tokens( self ):
        return { 'weather': self.current }

    def update( self ):

        current_time = time.time()
        elapsed = current_time - self.last_updated
        self.countdown -= elapsed
        if 0 < self.countdown:
            return

        #self.logger.debug( 'update timer elapsed' )

        # Reset the timer.
        self.countdown = self.refresh

        # Update weather.
        weather = None
        try:
            req = requests.get( self.url )
            weather = req.json()
        except RequestException as exc:
            self.logger.error( 'unable to fetch weather: %s', exc )
            return

        # Load the format from the config and put the requested weather items
        # from the fetched JSON into it.
        self.current = self.format
        current = weather['stats']['current']
        for token in current:
            self.current = self.current.replace(
                '<{}>'.format( token ),
                html.unescape( current[token] ) )

PLUGIN_TYPE = 'overlays'
PLUGIN_CLASS = WeatherOverlay
