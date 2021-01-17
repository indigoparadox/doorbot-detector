
from threading import Thread
import logging
import cv2
from .timer import FPSTimer

class Camera( Thread ):

    ''' This should run in the background and keep the stream moving so we
    don't waste time processing old frames. '''

    def __init__( self, **kwargs ):
        super().__init__()
        
        logger = logging.getLogger( 'camera.init' )

        logger.debug( 'setting up camera...' )

        self.w = 0
        self.h = 0
        self.running = True
        self._stream = cv2.VideoCapture( kwargs['url'] )

        self.timer = FPSTimer( self, **kwargs )

        self.notifiers = kwargs['notifiers']
        self.capturers = kwargs['capturers']
        self.observer_threads = kwargs['observers']
        self.detector_threads = kwargs['detectors']

        for thd in self.detector_threads:
            thd.cam = self
            thd.start()

        for thd in self.observer_threads:
            thd.start()

    def notify( self, subject, message ):
        for notifier in self.notifiers:
            notifier.send( subject, message )
    
    def run( self ):
        
        logger = logging.getLogger( 'camera.run' )
        
        logger.debug( 'starting camera loop...' )

        while self.running:
            self.timer.loop_timer_start()

            if self._stream.isOpened() and 0 >= self.w:
                self.w = \
                    int( self._stream.get( cv2.CAP_PROP_FRAME_WIDTH ) )
                logger.debug( 'video is {} wide'.format( self.w ) )
            if self._stream.isOpened() and 0 >= self.h:
                self.h = \
                    int( self._stream.get( cv2.CAP_PROP_FRAME_HEIGHT ) )
                logger.debug( 'video is {} high'.format( self.h ) )

            ret, frame = self._stream.read()

            for thd in self.detector_threads:
                #logger.debug( 'setting frame for {}...'.format( type( thd ) ) )
                thd.frame = frame

            for thd in self.observer_threads:
                #logger.debug( 'setting frame for {}...'.format( type( thd ) ) )
                thd.frame = frame

            self.timer.loop_timer_end()

