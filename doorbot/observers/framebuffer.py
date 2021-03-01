
from doorbot.cameras.rtsp import PLUGIN_CLASS, PLUGIN_TYPE
import logging

from doorbot.observers import ObserverThread

try:
    from cv2 import cv2
except ImportError:
    import cv2

class FramebufferThread( ObserverThread ):

    def __init__( self, **kwargs ):

        super().__init__( **kwargs )

        self.logger = logging.getLogger( 'observer.framebuffer' )

        self.logger.debug( 'setting up framebuffer...' )

        self.path = kwargs['path'] if 'path' in kwargs else '/dev/fb0'
        self.width = int( kwargs['width'] ) if 'width' in kwargs else None
        self.height = int( kwargs['height'] ) if 'height' in kwargs else None

    def run( self ):

        frame = None

        while self.running:
            self.timer.loop_timer_start()

            if not self._frame.frame_ready:
                self.logger.debug( 'waiting for frame...' )
                self.timer.loop_timer_end()
                continue

            with open( self.path, 'rb+' ) as framebuffer:
                frame = None
                with self._frame.get_frame() as orig_frame:
                    frame = orig_frame.copy()

                # Process the image for the framebuffer.
                frame = cv2.cvtColor( frame, cv2.COLOR_BGR2BGRA )
                if None != self.width and None != self.height:
                    frame = cv2.resize(
                        frame, (self.width, self.height) )

                #self.draw_overlay( frame )

                framebuffer.write( frame )

            self.timer.loop_timer_end()

PLUGIN_TYPE = 'observers'
PLUGIN_CLASS = FramebufferThread
