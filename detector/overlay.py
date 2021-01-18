
import threading
import logging
import requests
import json
import time
import html

class Overlays( threading.Thread ):

    def __init__( self ):
        super().__init__()
        self.running = True
        self.overlays = []

    def line( self, line ):
        line = line.replace( '<time>', time.strftime( '%H:%M:%S %m/%d/%Y' ) )
        for overlay in self.overlays:
            line = line.replace( overlay.token, overlay.current )
        return line

    def run( self ):

        while self.running:
            for overlay in self.overlays:
                overlay.update()

            time.sleep( 5 )

class OverlayHandler( object ):

    def __init__( self, **kwargs ):
        self.current = ''

class WeatherOverlay( OverlayHandler ):

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )
        self.token = '<weather>'
        self.url = kwargs['url']
        self.refresh = float( kwargs['refresh'] ) if 'refresh' in kwargs else \
            300
        self.last_updated = time.time()
        self.countdown = 0

    def update( self ):

        logger = logging.getLogger( 'overlay.weather' )

        current_time = time.time()
        elapsed = current_time - self.last_updated
        self.countdown -= elapsed
        if 0 < self.countdown:
            return

        logger.debug( 'update timer elapsed' )

        # Reset the timer.
        self.countdown = self.refresh

        # Update weather.
        r = requests.get( self.url )
        weather = r.json()

        current = weather['stats']['current']
        self.current = html.unescape( '{} {} {} {}'.format(
            current['outTemp'], current['humidity'], current['windSpeed'],
            current['rainRate'] ) )
