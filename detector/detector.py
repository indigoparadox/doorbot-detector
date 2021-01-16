
import cv2
import numpy
import logging
import time
from .capture import VideoCapture, PhotoCapture
from threading import Thread

CAPTURE_NONE = 0
CAPTURE_VIDEO = 1
CAPTURE_PHOTO = 2

class Detector( Thread ):

    ''' This grabs frames from the camera and detects stuff in them. '''

    def __init__( self, **kwargs ):

        super().__init__()

        logger = logging.getLogger( 'detector.init' )

        logger.debug( 'setting up detector...' )

        self.notifiers = kwargs['notifiers']

        self.min_w = int( kwargs['minw'] ) if 'minw' in kwargs else 0
        self.min_h = int( kwargs['minh'] ) if 'minh' in kwargs else 0
        self.ignore_edges = True if 'ignoreedges' in kwargs and \
            'true' == kwargs['ignoreedges'] else False
        logger.info( 'minimum movement size: {}x{}, ignore edges: {}'.format(
            self.min_w, self.min_h, self.ignore_edges ) )
        self.wait_max = int( kwargs['waitmax'] ) \
            if 'waitmax' in kwargs else 5
        self.running = True
        self.blur = int( kwargs['blur'] ) if 'blur' in kwargs else 5
        self.threshold = \
            int( kwargs['threshold'] ) if 'threshold' in kwargs else 127

        self.capturers = []
        if 'capture' in kwargs:
            cap_list = kwargs['capture'].split( ',' )
            if 'video' in cap_list:
                self.capturers.append( VideoCapture( **kwargs ) )
            if 'photo' in cap_list:
                self.capturers.append( PhotoCapture( **kwargs ) )

        logger.debug( 'threshold: {}'.format( self.threshold ) )
        logger.debug( 'blur: {}'.format( self.blur ) )

        self.back_sub = cv2.createBackgroundSubtractorMOG2(
            history=int( kwargs['history'] ) if 'history' in kwargs else 150,
            varThreshold=int( kwargs['varthreshold'] ) \
                if 'varthreshold' in kwargs else 25,
            detectShadows=True )

        self.kernel = numpy.ones( (20, 20), numpy.uint8 )

        self.cam = kwargs['camera']

        self.reserver = None
        if 'reserver' in kwargs and kwargs['reserver']:
            self.reserver = kwargs['reserver']

    def _notify( self, subject, message ):
        for notifier in self.notifiers:
            notifier.send( subject, message )
    
    def run( self ):

        wait_count = 0

        logger = logging.getLogger( 'detector.run' )

        logger.debug( 'starting detector loop...' )

        while self.running:
            res, frame = self.cam.frame()
            if not res:
                logger.warning( 'waiting...' )
                time.sleep( 1 )
                wait_count += 1
                if self.wait_max <= wait_count:
                    # Let systemd restart us.
                    raise Exception( 'waiting too long for camera!' )
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
                # Motion frames were found.

                max_idx = numpy.argmax( areas )

                cnt_iter = contours[max_idx]
                x, y, w, h = cv2.boundingRect( cnt_iter )

                if self.min_w > w or self.min_h > h:
                    # Filter out small movements.
                    self._notify( 'ignored', 'small {}x{} at {}, {}'.format(
                        w, h, x, y ) )

                elif self.ignore_edges and \
                (0 == w or \
                0 == h or \
                x + w >= self.cam.w or \
                y + h >= self.cam.h):
                    # Filter out edge movements.
                    self._notify( 'ignored', 'edge {}x{} at {}, {}'.format(
                        w, h, x, y ) )

                else:
                    # Process a valid movement.

                    for capturer in self.capturers:
                        capturer.append_motion( frame, self.cam.w, self.cam.h )

                    # TODO: Vary color based on type of object.
                    # TODO: Send notifier w/ summary of current objects.
                    # TODO: Make this summary retained.
                    # TODO: Send image data.
                    self._notify( 'movement', '{}x{} at {}, {}'.format(
                        w, h, x, y ) )

                    color = (255, 0, 0)
                    cv2.rectangle( frame, (x, y), (x + w, y + h), color, 3 )

            else:
                # No motion frames were found, digest capture pipeline.
                for capturer in self.capturers:
                    capturer.process_motion( frame, self.cam.w, self.cam.h )

            logger.debug( 'setting frame...' )
            if self.reserver:
                self.reserver.frame = frame

            # TODO: Smarter/configurable FPS limiter.
            time.sleep( 0.1 )

