
import cv2
import numpy
import logging
import time
from threading import Thread

class Detector( Thread ):

    ''' This grabs frames from the camera and detects stuff in them. '''

    def __init__( self, **kwargs ):

        super().__init__()

        logger = logging.getLogger( 'detector.init' )

        logger.debug( 'setting up detector...' )

        self.running = True
        self.blur = int( kwargs['blur'] ) if 'blur' in kwargs else 5
        self.threshold = \
            int( kwargs['threshold'] ) if 'threshold' in kwargs else 127

        # TODO: Create a mechanism to rinit this for day/night?
        self.back_sub = cv2.createBackgroundSubtractorMOG2(
            history=150,
            varThreshold=int( kwargs['varthreshold'] ) \
                if 'varthreshold' in kwargs else 25,
            detectShadows=True )

        self.kernel = numpy.ones( (20, 20), numpy.uint8 )

        self.cam = kwargs['camera']

        self.reserver = None
        if 'reserver' in kwargs and kwargs['reserver']:
            self.reserver = kwargs['reserver']
    
    def run( self ):

        logger = logging.getLogger( 'detector.run' )

        logger.debug( 'starting detector loop...' )

        while self.running:
            res, frame = self.cam.frame()
            if not res:
                logger.warning( 'waiting...' )
                time.sleep( 1 )
                continue

            logger.debug( 'processing frame...' )

            # Convert to foreground mask, close gabs, remove noise.
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
                x, y, w, h = cv2.boundingRect( cnt_iter )
                # TODO: Vary color based on type of object.
                color = (255, 0, 0)
                cv2.rectangle( frame, (x, y), (x + w, y + h), color, 3 )

            logger.debug( 'setting frame...' )
            if self.reserver:
                self.reserver.frame = frame

            # TODO: Smarter/configurable FPS limiter.
            time.sleep( 0.1 )

