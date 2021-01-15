
import cv2
import numpy
import logging
import time
from datetime import datetime
from threading import Thread

CAPTURE_NONE = 0
CAPTURE_VIDEO = 1
CAPTURE_PHOTO = 2

class CaptureEncoder( Thread ):
    def __init__( self, path, frames, w, h ):
        super().__init__()

        self.path = path
        self.frames = frames
        self.w = w
        self.h = h

    def run( self ):

        logger = logging.getLogger( 'detector.capture.encoder' )

        logger.info( 'encoding {} ({} frames)...'.format(
            self.path, len( self.frames ) ) )

        fourcc = cv2.VideoWriter_fourcc( *'MP4V' )
        encoder = \
            cv2.VideoWriter( self.path, fourcc, 20.0, (self.w, self.h) )
        for frame in self.frames:
            encoder.write( frame )
        encoder.release()

        logger.info( 'encoding {} completed'.format( self.path ) )

class Detector( Thread ):

    ''' This grabs frames from the camera and detects stuff in them. '''

    def __init__( self, **kwargs ):

        super().__init__()

        logger = logging.getLogger( 'detector.init' )

        logger.debug( 'setting up detector...' )

        self.notifiers = kwargs['notifiers']

        self.snapshots = kwargs['snapshots'] if 'snapshots' in kwargs else '/tmp'
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

        self.capture = []
        if 'capture' in kwargs:
            cap_list = kwargs['capture'].split( ',' )
            if 'video' in cap_list:
                self.capture.append( CAPTURE_VIDEO )
                logger.info( 'capturing videos' )
            if 'photo' in cap_list:
                self.capture.append( CAPTURE_PHOTO )
                logger.info( 'capturing photos' )

        self.capture_frames = []

        logger.info( 'saving snapshots to {}'.format( self.snapshots ) )

        logger.debug( 'threshold: {}'.format( self.threshold ) )
        logger.debug( 'blur: {}'.format( self.blur ) )

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
                max_idx = numpy.argmax( areas )

                cnt_iter = contours[max_idx]
                x, y, w, h = cv2.boundingRect( cnt_iter )

                if self.min_w > w or self.min_h > h:
                    self._notify( 'ignored', 'small {}x{} at {}, {}'.format(
                        w, h, x, y ) )
                elif self.ignore_edges and \
                (0 == w or \
                0 == h or \
                x + w >= self.cam.w or \
                y + h >= self.cam.h):
                    self._notify( 'ignored', 'edge {}x{} at {}, {}'.format(
                        w, h, x, y ) )
                else:

                    timestamp = datetime.now().strftime(
                        '%Y-%m-%d-%H-%M-%S-%f' )
                    if CAPTURE_PHOTO in self.capture:
                        cv2.imwrite( '{}/{}.jpg'.format(
                            self.snapshots, timestamp ), frame )
                    if CAPTURE_VIDEO in self.capture:
                        if 0 == len( self.capture_frames ):
                            self.capture_timestamp = datetime.now().strftime(
                                '%Y-%m-%d-%H-%M-%S-%f' )
                        self.capture_frames.append( frame.copy() )

                    # TODO: Vary color based on type of object.
                    # TODO: Send notifier w/ summary of current objects.
                    # TODO: Make this summary retained.
                    # TODO: Send image data.
                    self._notify( 'movement', '{}x{} at {}, {} ({}f)'.format(
                        w, h, x, y, len( self.capture_frames ) ) )

                    color = (255, 0, 0)
                    cv2.rectangle( frame, (x, y), (x + w, y + h), color, 3 )
            elif 0 < len( self.capture_frames ):
                if CAPTURE_VIDEO in self.capture:
                    # Ship the frames off to a separate thread to write out.
                    encoder = CaptureEncoder( 
                        '{}/{}.mp4'.format(
                            self.snapshots,
                            self.capture_timestamp ),
                        self.capture_frames,
                        self.cam.w,
                        self.cam.h )
                    self.capture_frames = []
                    encoder.start()

            logger.debug( 'setting frame...' )
            if self.reserver:
                self.reserver.frame = frame

            # TODO: Smarter/configurable FPS limiter.
            time.sleep( 0.1 )

