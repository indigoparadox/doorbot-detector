
import threading
import time
import re
import logging

class Overlays( threading.Thread ):

    def __init__( self, **kwargs ):
        super().__init__()
        self.running = True
        self._overlays = {}
        self.highlights = {}
        self.daemon = True
        self.logger = logging.getLogger( 'overlays' )
        self.refresh = kwargs['refresh'] if 'refresh' in kwargs else 5

    def add_overlay( self, key, overlay ):
        overlay.master = self
        self._overlays[key] = overlay

    def tokenize( self, text ):

        ''' Given a line of text (nominally specified in the config), replace
        tokens in it with tokens provided by loaded overlays. '''

        for overlay_key in self._overlays:
            # TODO: Limit to instances.
            overlay = self._overlays[overlay_key]
            for token, replace in overlay.tokens.items():
                text = text.replace( '<{}.{}>'.format( token, overlay_key ), replace )

        return text

    def text_height( self, text, **kwargs ): # pylint: disable=unused-argument

        return 0

    def text( self, frame, text, position ): # pylint: disable=unused-argument

        ''' Draw text on the frame. This should be overridden by the
        implementation-specific overlay handler. '''

        return frame

    def rect( self, frame, x1, y1, x2, y2, color, **kwargs ): # pylint: disable=unused-argument, invalid-name

        ''' Draw a rectangle on the frame. This should be overridden by the
        implementation-specific overlay handler. '''

        return frame

    def draw( self, frame, **kwargs ):

        ''' This should NOT be overridden directly, but the methods it uses
        (such as .text()) should be overridden by the implementation=specific
        overlay master. Uses kwargs passed from config of the observer whose
        frame it's drawing to. '''

        # Handle general kwargs.
        overlay_text = kwargs['overlay'] if 'overlay' in kwargs else ''
        overlay_line_height = self.text_height( 'A', **kwargs )
        overlay_coords = \
            tuple( [int( x ) for x in kwargs['overlaycoords'].split( ',' )] ) \
            if 'overlaycoords' in kwargs else (10, 10)

        # Bump coords down, since they start from text bottom.
        overlay_coords = (overlay_coords[0], overlay_coords[1] + overlay_line_height)

        # Allow overlays to draw graphics.
        for overlay_key in self._overlays:
            # TODO: Limit to instances.
            overlay = self._overlays[overlay_key]
            overlay.draw( frame )

        # Draw text provided by simple text-only overlays.
        text = overlay_text.split( "\\n" )
        origin = overlay_coords
        for line in text:
            line = self.tokenize( line )
            #line = self.filter.sub( '', line )
            line = ''.join( c for c in line if c in \
                'abcdefghijklmnopqrstuvwxyz' + \
                'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .></%$,:#@&*()?_-=+!' )
            self.text( frame, line, origin, **kwargs )
            origin = (origin[0], origin[1] + overlay_line_height + 5)

        return frame

    def run( self ):

        while self.running:
            for overlay_key in self._overlays:
                overlay = self._overlays[overlay_key]
                try:
                    overlay.update()
                except Exception as exc: # pylint: disable=broad-except
                    self.logger.exception( exc )

            time.sleep( self.refresh )

    def stop( self ):
        self.running = False

class OverlayHandler( object ):

    def __init__( self, **kwargs ): # pylint: disable=unused-argument
        self.current = ''
        self.master = None

    @property
    def tokens( self ):
        return {}

    def draw( self, frame, **kwargs ): # pylint: disable=unused-argument

        ''' Draw overlay on the frame. This can be overridden by overlays that
        want to draw graphics. Simpler overlays can just provide tokens. '''

        return frame

    def update( self ):
        pass
