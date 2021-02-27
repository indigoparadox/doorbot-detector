#!/usr/bin/env python3

import logging
import argparse
from configparser import ConfigParser
from doorbot.notifier import MQTTNotifier, LoggerNotifier
from doorbot.capture import VideoCapture, PhotoCapture
from doorbot.observer import ReserverThread, FramebufferThread
from doorbot.detector import MotionDetector
from doorbot.camera import IPCamera
from doorbot.overlay import Overlays, WeatherOverlay

def load_module_config( config, key ):
    out_cfg = {}
    try:
        out_cfg = dict( config.items( key ) )
    except Exception as e:
        logging.error( e )

    if 'enable' in out_cfg and 'true' == out_cfg['enable']:
        return out_cfg

    return None

logger = None

def main():

    global logger

    parser = argparse.ArgumentParser()

    verbosity_grp = parser.add_mutually_exclusive_group()

    verbosity_grp.add_argument( '-v', '--verbose', action='store_true' )

    verbosity_grp.add_argument( '-q', '--quiet', action='store_true' )

    parser.add_argument(
        '-c', '--config', action='store', default='detector.ini' )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig( level=logging.DEBUG )
        logging.getLogger( 'doorbot.run' ).setLevel( logging.INFO )
        logging.getLogger( 'doorbot.process' ).setLevel( logging.WARNING )
        logging.getLogger( 'camera.process' ).setLevel( logging.WARNING )
        logging.getLogger( 'framelock' ).setLevel( logging.ERROR )
    elif args.quiet:
        logging.basicConfig( level=logging.ERROR )
    else:
        logging.basicConfig( level=logging.INFO )
        logging.getLogger( 'framelock' ).setLevel( logging.ERROR )
    logger = logging.getLogger( 'main' )

    config = ConfigParser()
    config.read( args.config )

    # Setup the notifier.

    notifiers = []

    notifiers.append( LoggerNotifier() )

    mqtt_cfg = load_module_config( config, 'mqtt' )
    if None != mqtt_cfg:
        notifiers.append( MQTTNotifier( **mqtt_cfg ) )

    # Add capturer utilities.

    capturers = []

    vcap_cfg = load_module_config( config, 'videocap' )
    if None != vcap_cfg:
        capturers.append( VideoCapture( **vcap_cfg ) )

    pcap_cfg = load_module_config( config, 'photocap' )
    if None != pcap_cfg:
        capturers.append( PhotoCapture( **pcap_cfg ) )

    # Setup the detector and observer satellite threads.

    observer_threads = []

    fb_cfg = load_module_config( config, 'framebuffer' )
    if None != fb_cfg:
        observer_threads.append( FramebufferThread( **fb_cfg ) )

    rsrv_cfg = load_module_config( config, 'reserver' )
    if None != rsrv_cfg:
        observer_threads.append( ReserverThread( **rsrv_cfg ) )

    detector_threads = []
    motion_cfg = load_module_config( config, 'motiondetect' )
    if None != motion_cfg:
        detector_threads.append( MotionDetector( **motion_cfg ) )

    overlay_thread = Overlays()

    weather_cfg = load_module_config( config, 'weather' )
    if None != weather_cfg:
        overlay_thread.overlays.append( WeatherOverlay( **weather_cfg ) )

    # Setup the camera, the star of the show.

    cam_cfg = dict( config.items( 'stream' ) )
    cam_cfg['notifiers'] = notifiers
    cam_cfg['capturers'] = capturers
    cam_cfg['observers'] = observer_threads
    cam_cfg['detectors'] = detector_threads
    cam_cfg['overlays'] = overlay_thread
    app = IPCamera( **cam_cfg )

    app.start()
    app.join()

if '__main__' == __name__:
    try:
        main()
    except KeyboardInterrupt as e:
        logger.info( 'quitting on ctrl-c' )
