
import logging
import threading

import numpy
try:
    from cv2 import cv2
except ImportError:
    import cv2

from .util import FPSTimer, FrameLock

CAPTURE_NONE = 0
CAPTURE_VIDEO = 1
CAPTURE_PHOTO = 2

class DetectionEvent( object ):

    ''' Simple structure describing movement or activity in a frame. '''

    def __init__( self, event_type, dimensions, position, frame ):
        self.event_type = event_type
        self.dimensions = dimensions
        self.position = position
        self.frame = frame

class Detector( threading.Thread ):

    ''' This grabs frames from the camera and detects stuff in them. '''

    def __init__( self, **kwargs ):

        super().__init__()

        self._source_lock = threading.Lock()
        self._frame = FrameLock()
        self._frame_processed = True
        self.daemon = True
        self.running = True
        self.cam = None

        self.timer = FPSTimer( self, **kwargs )

    def set_frame( self, value ):
        self._frame.set_frame( value )
        self._frame_processed = False

    def detect( self, frame ):

        ''' Process a given frame against current object state to determine
        if movement or other activity has occurred. Return a DetectionEvent
        object describing the result. '''

        return DetectionEvent(
            'ignored', (0, 0), (0, 0), None )

    def run( self ):

        ''' Main loop for detection thread. Dispatch relevant messages to other
        threads based on detected activity. '''

        logger = logging.getLogger( 'detector.run' )

        logger.debug( 'starting detector loop...' )

        while self.running:
            self.timer.loop_timer_start()

            # Spin until we have a new frame to process.
            if self._frame_processed or not self._frame.frame_ready:
                logger.debug( 'waiting for frame...' )
                self.timer.loop_timer_end()
                continue

            logger.debug( 'processing frame...' )

            frame = None
            with self._frame.get_frame() as orig_frame:
                frame = orig_frame.copy()

            # TODO: Move elsewhere.
            if hasattr( self.cam, 'overlays' ):
                if 'motion' not in self.cam.overlays.highlights:
                    self.cam.overlays.highlights['motion'] = {'boxes': []}
                self.cam.overlays.highlights['motion']['boxes'] = []

            event = self.detect( frame )
            if event and 'movement' == event.event_type:
                for capturer in self.cam.capturers:
                    capturer.handle_motion_frame( frame, self.cam.w, self.cam.h )

                # TODO: Send notifier w/ summary of current objects.
                # TODO: Make this summary retained.
                # TODO: Send image data.
                ret, jpg = cv2.imencode( '.jpg', event.frame )
                self.cam.notify( 'movement', '{} at {}'.format(
                    event.dimensions, event.position ), snapshot=jpg.tostring() )

                # TODO: Vary color based on type of object.
                color = (255, 0, 0)
                self.cam.overlays.highlights['motion']['boxes'].append( {
                    'x1': event.position[0], 'y1': event.position[1],
                    'x2': event.position[0] + event.dimensions[0],
                    'y2': event.position[1] + event.dimensions[1],
                    'color': color
                } )
            else:
                # No motion frames were found, digest capture pipeline.
                for capturer in self.cam.capturers:
                    capturer.finalize_motion( frame, self.cam.w, self.cam.h )

            self.timer.loop_timer_end()

class MotionDetector( Detector ):

    ''' Specialized detector that looks for motion accross frames. '''

    def __init__( self, **kwargs ):

        super().__init__( **kwargs )

        logger = logging.getLogger( 'detector.motion.init' )

        logger.debug( 'setting up motion detector...' )

        # Grab configuration params.
        self.min_w = int( kwargs['minw'] ) if 'minw' in kwargs else 0
        self.min_h = int( kwargs['minh'] ) if 'minh' in kwargs else 0
        self.ignore_edges = True if 'ignoreedges' in kwargs and \
            'true' == kwargs['ignoreedges'] else False
        logger.debug( 'minimum movement size: %dx%d, ignore edges: %d',
            self.min_w, self.min_h, self.ignore_edges )
        self.wait_max = int( kwargs['waitmax'] ) \
            if 'waitmax' in kwargs else 5
        self.running = True
        self.blur = int( kwargs['blur'] ) if 'blur' in kwargs else 5
        self.threshold = \
            int( kwargs['threshold'] ) if 'threshold' in kwargs else 127

        # Setup OpenCV stuff.
        self.back_sub = cv2.createBackgroundSubtractorMOG2(
            history=int( kwargs['history'] ) if 'history' in kwargs else 150,
            varThreshold=int( kwargs['varthreshold'] ) \
                if 'varthreshold' in kwargs else 25,
            detectShadows=True )
        self.kernel = numpy.ones( (20, 20), numpy.uint8 )

        logger.debug( 'threshold: %d', self.threshold )
        logger.debug( 'blur: %d', self.blur )

    def handle_movement( self, frame, rect_x, rect_y, rect_w, rect_h ):

        ''' Motion frames were found. '''

        if self.min_w > rect_w or self.min_h > rect_h:
            # Filter out small movements.
            #self.cam.notify( 'ignored', 'small {}x{} at {}, {}'.format(
            #    w, h, x, y ) )
            pass

        elif self.ignore_edges and \
        (0 == rect_w or \
        0 == rect_h or \
        rect_x + rect_w >= self.cam.w or \
        rect_y + rect_h >= self.cam.h):
            # Filter out edge movements.
            return DetectionEvent(
                'ignored', (rect_w, rect_h), (rect_x, rect_y), frame )

        else:
            # Process a valid movement.
            return DetectionEvent(
                'movement', (rect_w, rect_h), (rect_x, rect_y), frame )

    def detect( self, frame ):

        # Convert to foreground mask, close gaps, remove noise.
        fg_mask = self.back_sub.apply( frame )
        fg_mask = cv2.morphologyEx( fg_mask, cv2.MORPH_CLOSE, self.kernel )
        fg_mask = cv2.medianBlur( fg_mask, self.blur )

        # Flatten mask to B&W.
        ret, fg_mask = cv2.threshold(
            fg_mask, self.threshold, 255, cv2.THRESH_BINARY )

        # Find object contours/areas.
        contours, hierarchy = cv2.findContours(
            fg_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE )[-2:]
        areas = [cv2.contourArea(c) for c in contours]

        if 0 < len( areas ):

            max_idx = numpy.argmax( areas )

            cnt_iter = contours[max_idx]
            rect_x, rect_y, rect_w, rect_h = cv2.boundingRect( cnt_iter )
            
            return self.handle_movement( frame, rect_x, rect_y, rect_w, rect_h )

        return None
