
try:
    from cv2 import cv2
except ImportError:
    import cv2

from . import Overlays

class OpenCVOverlays( Overlays ):

    ''' Module with OpenCV-specific image handling for drawing overlays onto
    frames. '''

    def rect( self, frame, x1, y1, x2, y2, color, **kwargs ):

        cv2.rectangle( frame,
            (x1, y1),
            (x2, y2), color, 3 )

        return frame

    def text_height( self, text, **kwargs ):

        overlay_font = \
            getattr( cv2, 'FONT_{}'.format( kwargs['overlayfont'] ) ) \
            if 'overlayfont' in kwargs else cv2.FONT_HERSHEY_SIMPLEX
        overlay_scale = float( kwargs['overlayscale'] ) \
            if 'overlayscale' in kwargs else 0.5
        overlay_thickness = int( kwargs['overlaythickness'] ) \
            if 'overlaythickness' in kwargs else 1

        size = cv2.getTextSize(
            text, fontFace=overlay_font, fontScale=overlay_scale,
            thickness=overlay_thickness * 4 )

        return size[0][1]

    def text( self, frame, text, position, **kwargs ):

        # Handle OpenCV-specific kwargs.
        overlay_color = \
            tuple( [int( x ) for x in kwargs['overlaycolor'].split( ',' )] ) \
            if 'overlaycolor' in kwargs else (255, 255, 255)
        overlay_font = \
            getattr( cv2, 'FONT_{}'.format( kwargs['overlayfont'] ) ) \
            if 'overlayfont' in kwargs else cv2.FONT_HERSHEY_SIMPLEX
        overlay_scale = float( kwargs['overlayscale'] ) \
            if 'overlayscale' in kwargs else 0.5
        overlay_thickness = int( kwargs['overlaythickness'] ) \
            if 'overlaythickness' in kwargs else 1

        cv2.putText(
            frame, text, position, overlay_font,
            overlay_scale, (0, 0, 0), overlay_thickness * 4,
            cv2.LINE_AA )

        cv2.putText(
            frame, text, position, overlay_font,
            overlay_scale, overlay_color, overlay_thickness,
            cv2.LINE_AA )

        return frame
