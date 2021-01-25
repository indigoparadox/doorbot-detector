
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
        self.highlights = {}
        self.daemon = True

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

    def update( self ):
        pass

class WeatherOverlay( OverlayHandler ):

    def __init__( self, **kwargs ):
        super().__init__( **kwargs )
        self.token = '<weather>'
        self.url = kwargs['url']
        self.refresh = float( kwargs['refresh'] ) if 'refresh' in kwargs else \
            300
        self.last_updated = time.time()
        self.countdown = 0
        self.format = kwargs['format'] if 'format' in kwargs else '<outTemp>'

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
        weather = None
        try:
            r = requests.get( self.url )
            weather = r.json()
        except Exception as e:
            logger.error( 'unable to fetch weather: {}'.format( e ) )
            return

        self.current = self.format
        current = weather['stats']['current']
        for token in current:
            self.current = self.current.replace(
                '<{}>'.format( token ),
                html.unescape( current[token] ) )

