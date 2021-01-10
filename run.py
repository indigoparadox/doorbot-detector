#!/usr/bin/env python3

import os
import logging
import threading
import argparse
from detector.reserver import ReserverThread
from detector.detector import Detector
from detector.camera import Camera
from configparser import ConfigParser

def main():
    
    parser = argparse.ArgumentParser()

    verbosity_grp = parser.add_mutually_exclusive_group()

    verbosity_grp.add_argument( '-v', '--verbose', action='store_true' )

    verbosity_grp.add_argument( '-q', '--quiet', action='store_true' )

    parser.add_argument( '-c', '--config', action='store' )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig( level=logging.DEBUG )
    elif args.quiet:
        logging.basicConfig( level=logging.ERROR )
    else:
        logging.basicConfig( level=logging.INFO )

    logging.getLogger( 'detector.run' ).setLevel( logging.INFO )

    config = ConfigParser()
    config.read( args.config )

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

