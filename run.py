#!/usr/bin/env python3

import os
import logging
import threading
import argparse
from detector.notifier import MQTTNotifier, LoggerNotifier
from detector.capture import VideoCapture, PhotoCapture
from detector.observer import ReserverThread, FramebufferThread
from detector.detector import Detector
from detector.camera import Camera
from configparser import ConfigParser

def load_module_config( config, key ):
    out_cfg = {}
    try:
        out_cfg = dict( config.items( key ) )
    except Exception as e:
        logging.error( e )

    if 'enable' in out_cfg and 'true' == out_cfg['enable']:
        return out_cfg

    return None

def main():
    
    parser = argparse.ArgumentParser()

    verbosity_grp = parser.add_mutually_exclusive_group()

    verbosity_grp.add_argument( '-v', '--verbose', action='store_true' )

    verbosity_grp.add_argument( '-q', '--quiet', action='store_true' )

    parser.add_argument( '-c', '--config', action='store' )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig( level=logging.DEBUG )
        logging.getLogger( 'detector.run' ).setLevel( logging.INFO )
        logging.getLogger( 'detector.run.movement' ).setLevel( logging.DEBUG )
    elif args.quiet:
        logging.basicConfig( level=logging.ERROR )
    else:
        logging.basicConfig( level=logging.INFO )
        logging.getLogger( 'detector.run' ).setLevel( logging.INFO )
        logging.getLogger( 'detector.run.movement' ).setLevel( logging.DEBUG )

    config = ConfigParser()
    config.read( args.config )

    # Setup the camera and reserver satellite threads.

    cam = Camera( config['stream']['url'] )
    cam.start()

    # Setup the notifier.

    notifiers = []

    notifiers.append( LoggerNotifier() )

    mqtt_cfg = load_module_config( config, 'mqtt' )
    if None != mqtt_cfg:
        notifiers.append( MQTTNotifier( **mqtt_cfg ) )

    capturers = []

    vcap_cfg = load_module_config( config, 'videocap' )
    if None != vcap_cfg:
        capturers.append( VideoCapture( **vcap_cfg ) )
        
    pcap_cfg = load_module_config( config, 'photocap' )
    if None != pcap_cfg:
        capturers.append( PhotoCapture( **pcap_cfg ) )
    
    observer_threads = []

    fb_cfg = load_module_config( config, 'framebuffer' )
    if None != fb_cfg:
        observer_threads.append( FramebufferThread( **fb_cfg ) )

    rsrv_cfg = load_module_config( config, 'reserver' )
    if None != rsrv_cfg:
        observer_threads.append( ReserverThread( **rsrv_cfg ) )

    # Setup the detector, the star of the show.

    detector_cfg = dict( config.items( 'stream' ) )
    detector_cfg['camera'] = cam
    detector_cfg['notifiers'] = notifiers
    detector_cfg['capturers'] = capturers
    detector_cfg['observers'] = observer_threads
    app = Detector( **detector_cfg )
    app.start()
    app.join()

if '__main__' == __name__:
    main()

