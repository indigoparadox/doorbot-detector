
import logging

try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.cameras import Camera

class OpenCVCamera( Camera ):

    ''' Simple camera interface using OpenCV.

    Attempts to stay connected to camera through interruptions. '''

    def __init__( self, instance_name, **kwargs ):

        self.attempts = 0

        self.logger = logging.getLogger( 'camera.opencv' )

        # Try as a numerical index first, falling back to a string URL.
        try:
            self.cam_url = int( kwargs['url'] )
        except ValueError:
            self.logger.info( '%s seems to be a remote URL...', kwargs['url'] )
            self.cam_url = kwargs['url']
        self._stream = cv2.VideoCapture( self.cam_url )

        super().__init__( instance_name, **kwargs )

    def run( self ):

        self.logger.debug( 'starting camera loop...' )

        while self.running:
            self.timer.loop_timer_start()

            if self._stream.isOpened() and 0 >= self.width:
                self.width = \
                    int( self._stream.get( cv2.CAP_PROP_FRAME_WIDTH ) )
                self.logger.info( 'video is %d wide', self.width )
            if self._stream.isOpened() and 0 >= self.height:
                self.height = \
                    int( self._stream.get( cv2.CAP_PROP_FRAME_HEIGHT ) )
                self.logger.info( 'video is %d high', self.height )

            ret, frame = self._stream.read()

            if not ret:
                self.logger.warning( 'camera disconnected!' )
                self._stream.release()
                self.attempts += 1
                self.logger.info( 'reconnecting (attempt %d)', self.attempts )
                self._stream.open( self.cam_url )
                self.timer.loop_timer_end()
                continue

            self.attempts = 0

            self.frame = frame

            self.timer.loop_timer_end()

PLUGIN_CLASS = OpenCVCamera # pylint: disable=invalid-name
PLUGIN_TYPE = 'cameras'
