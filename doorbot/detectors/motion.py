
import logging

import numpy
try:
    from cv2 import cv2
except ImportError:
    import cv2

from doorbot.detectors import Detector, DetectionEvent

class MotionDetector( Detector ):

    ''' Specialized detector that looks for motion accross frames. '''

    def __init__( self, instance_name, **kwargs ):
        
        super().__init__( instance_name, **kwargs )

        self.logger = logging.getLogger( 'detector.motion.{}'.format( instance_name ) )

        self.logger.debug( 'setting up motion detector...' )

        # Grab configuration params.
        self.min_w = int( kwargs['minw'] ) if 'minw' in kwargs else 0
        self.min_h = int( kwargs['minh'] ) if 'minh' in kwargs else 0
        self.ignore_edges = True if 'ignoreedges' in kwargs and \
            'true' == kwargs['ignoreedges'] else False
        self.logger.debug( 'minimum movement size: %dx%d, ignore edges: %d',
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

        self.logger.debug( 'threshold: %d', self.threshold )
        self.logger.debug( 'blur: %d', self.blur )

    def handle_movement( self, frame : numpy.ndarray, rect_x, rect_y, rect_w, rect_h ):

        ''' Motion frames were found. '''

        cam_w = frame.shape[0]
        cam_h = frame.shape[1]

        if self.min_w > rect_w or self.min_h > rect_h:
            # Filter out small movements.
            #self.cam.notify( 'ignored', 'small {}x{} at {}, {}'.format(
            #    w, h, x, y ) )
            pass

        elif self.ignore_edges and \
        (0 == rect_w or \
        0 == rect_h or \
        rect_x + rect_w >= cam_w or \
        rect_y + rect_h >= cam_h):
            # Filter out edge movements.
            return DetectionEvent(
                'ignored', (rect_w, rect_h), (rect_x, rect_y), frame )

        else:
            # Process a valid movement.
            return DetectionEvent(
                'movement', (rect_w, rect_h), (rect_x, rect_y), frame )

    def detect( self, frame : numpy.ndarray ):

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

PLUGIN_TYPE = 'detectors'
PLUGIN_CLASS = MotionDetector
