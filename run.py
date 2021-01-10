#!/usr/bin/env python3

import os
import logging
import threading
from detector.reserver import ReserverThread
from detector.detector import Detector
from detector.camera import Camera
from configparser import ConfigParser

def main():
    logging.basicConfig( level=logging.DEBUG )
    config = ConfigParser()
    config.read( 'detector.ini' )

    # Setup the camera and reserver satellite threads.

    cam = Camera( config['stream']['url'] )
    cam.start()

    reserver_cfg = dict( config.items( 'reserver' ) )
    reserver_thread = ReserverThread( **reserver_cfg )
    reserver_thread.start()

    # Setup the detector, the star of the show.

    detector_cfg = dict( config.items( 'stream' ) )
    detector_cfg['reserver'] = reserver_thread.server
    detector_cfg['camera'] = cam
    app = Detector( **detector_cfg )
    app.start()
    app.join()

if '__main__' == __name__:
    main()

