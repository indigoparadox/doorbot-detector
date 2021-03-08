
import threading
import time
import re

class Overlays( threading.Thread ):

    def __init__( self, **kwargs ):
        super().__init__()
        self.running = True
        self._overlays = []
        self.highlights = {}
        self.daemon = True
        self.refresh = kwargs['refresh'] if 'refresh' in kwargs else 5

    def add_overlay( self, overlay ):
        overlay.master = self
        self._overlays.append( overlay )

    def tokenize( self, text ):

        ''' Given a line of text (nominally specified in the config), replace 
        tokens in it with tokens provided by loaded overlays. '''

        for overlay in self._overlays:
            for token, replace in overlay.tokens.items():
                text = text.replace( '<{}>'.format( token ), replace )

        return text

    def text( self, frame, text, position ):

        ''' Draw text on the frame. This should be overridden by the
        implementation-specific overlay handler. '''

        return frame

    def rect( self, frame, x1, y1, x2, y2, color, **kwargs ):

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
        overlay_coords = \
            tuple( [int( x ) for x in kwargs['overlaycoords'].split( ',' )] ) \
            if 'overlaycoords' in kwargs else (10, 10)
        overlay_line_height = int( kwargs['overlaylineheight'] ) \
            if 'overlaylineheight' in kwargs else 20

        # Allow overlays to draw graphics.
        for overlay in self._overlays:
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
            line = self.text( frame, line, origin, **kwargs )
            # TODO: Measure text line for Y-height.
            origin = (origin[0], origin[1] + overlay_line_height)

        return frame

    def run( self ):

        while self.running:
            for overlay in self._overlays:
                overlay.update()

            time.sleep( self.refresh )

class OverlayHandler( object ):

    def __init__( self, **kwargs ):
        self.current = ''
        self.master = None

    @property
    def tokens( self ):
        return {}

    def draw( self, frame, **kwargs ):

        ''' Draw overlay on the frame. This can be overridden by overlays that
        want to draw graphics. Simpler overlays can just provide tokens. '''

        return frame

    def update( self ):
        pass
