#!/usr/bin/env python3

import cv2
import random
import logging

from detector.detector import MotionDetector

person_seq = [
    'testdata/motion1/2021-01-10-14-09-45-065179.jpg',
    'testdata/motion1/2021-01-10-14-09-45-275090.jpg',
    'testdata/motion1/2021-01-10-14-09-45-498608.jpg',
    'testdata/motion1/2021-01-10-14-09-45-922941.jpg',
    'testdata/motion1/2021-01-10-14-09-46-809458.jpg',
    'testdata/motion1/2021-01-10-14-09-47-057291.jpg',
    'testdata/motion1/2021-01-10-14-09-47-692810.jpg']

shadow_seq = [
    'testdata/motion2/2021-01-12-23-07-59-881639.jpg',
    'testdata/motion2/2021-01-12-23-08-00-095573.jpg',
    'testdata/motion2/2021-01-12-23-08-00-309626.jpg',
    'testdata/motion2/2021-01-12-23-08-00-522949.jpg',
    'testdata/motion2/2021-01-12-23-08-00-737358.jpg',
    'testdata/motion2/2021-01-12-23-08-00-954548.jpg',
    'testdata/motion2/2021-01-12-23-08-01-177885.jpg',
    'testdata/motion2/2021-01-12-23-08-01-404122.jpg',
    'testdata/motion2/2021-01-12-23-08-01-634454.jpg',
    'testdata/motion2/2021-01-12-23-08-03-265788.jpg',
    'testdata/motion2/2021-01-12-23-08-03-487155.jpg',
    'testdata/motion2/2021-01-12-23-08-03-711782.jpg',
    'testdata/motion2/2021-01-12-23-08-03-925026.jpg',
    'testdata/motion2/2021-01-12-23-08-15-416192.jpg',
    'testdata/motion2/2021-01-12-23-08-15-638973.jpg',
    'testdata/motion2/2021-01-12-23-08-15-860821.jpg',
    'testdata/motion2/2021-01-12-23-08-16-084549.jpg',
    'testdata/motion2/2021-01-12-23-08-16-308076.jpg',
    'testdata/motion2/2021-01-12-23-08-16-533362.jpg',
    'testdata/motion2/2021-01-12-23-08-16-758369.jpg',
    'testdata/motion2/2021-01-12-23-08-16-982579.jpg',
    'testdata/motion2/2021-01-12-23-08-17-207349.jpg',
    'testdata/motion2/2021-01-12-23-08-17-435080.jpg',
    'testdata/motion2/2021-01-12-23-08-17-662835.jpg',
    'testdata/motion2/2021-01-12-23-08-17-887460.jpg',
    'testdata/motion2/2021-01-12-23-08-18-117406.jpg',
    'testdata/motion2/2021-01-12-23-08-18-341646.jpg',
    'testdata/motion2/2021-01-12-23-08-18-564876.jpg',
    'testdata/motion2/2021-01-12-23-08-18-787726.jpg',
    'testdata/motion2/2021-01-12-23-08-19-011816.jpg',
    'testdata/motion2/2021-01-12-23-08-19-233959.jpg',
    'testdata/motion2/2021-01-12-23-08-46-913766.jpg',
    'testdata/motion2/2021-01-12-23-08-47-128488.jpg',
    'testdata/motion2/2021-01-12-23-08-47-343600.jpg',
    'testdata/motion2/2021-01-12-23-08-47-559815.jpg',
    'testdata/motion2/2021-01-12-23-08-47-774688.jpg',
    'testdata/motion2/2021-01-12-23-08-48-605368.jpg',
    'testdata/motion2/2021-01-12-23-08-48-823326.jpg',
    'testdata/motion2/2021-01-12-23-08-49-041308.jpg',
    'testdata/motion2/2021-01-12-23-08-49-260108.jpg',
    'testdata/motion2/2021-01-12-23-08-49-476176.jpg',
    'testdata/motion2/2021-01-12-23-08-49-693758.jpg',
    'testdata/motion2/2021-01-12-23-08-49-914624.jpg',
    'testdata/motion2/2021-01-12-23-08-50-135251.jpg',
    'testdata/motion2/2021-01-12-23-08-50-354529.jpg',
    'testdata/motion2/2021-01-12-23-08-50-568536.jpg',
    'testdata/motion2/2021-01-12-23-09-33-679368.jpg',
    'testdata/motion2/2021-01-12-23-09-33-897115.jpg',
    'testdata/motion2/2021-01-12-23-09-34-111835.jpg',
    'testdata/motion2/2021-01-12-23-09-36-178436.jpg',
    'testdata/motion2/2021-01-12-23-09-36-395404.jpg',
    'testdata/motion2/2021-01-12-23-09-36-613862.jpg',
    'testdata/motion2/2021-01-12-23-09-36-831245.jpg',
    'testdata/motion2/2021-01-12-23-09-37-663070.jpg',
    'testdata/motion2/2021-01-12-23-09-37-880460.jpg',
    'testdata/motion2/2021-01-12-23-09-38-104629.jpg',
    'testdata/motion2/2021-01-12-23-09-38-321666.jpg',
    'testdata/motion2/2021-01-12-23-09-38-547333.jpg',
    'testdata/motion2/2021-01-12-23-09-38-765123.jpg',
    'testdata/motion2/2021-01-12-23-09-38-989303.jpg',
    'testdata/motion2/2021-01-12-23-09-39-216232.jpg',
    'testdata/motion2/2021-01-12-23-09-39-446119.jpg',
    'testdata/motion2/2021-01-12-23-09-39-668852.jpg',
    'testdata/motion2/2021-01-12-23-09-39-885316.jpg',
    'testdata/motion2/2021-01-12-23-09-40-110300.jpg',
    'testdata/motion2/2021-01-12-23-09-40-326435.jpg',
    'testdata/motion2/2021-01-12-23-09-40-542747.jpg',
    'testdata/motion2/2021-01-12-23-09-40-766118.jpg']
        
initial_config = {
    'threshold': 50,
    'varthreshold': 200,
    'blur': 5,
    'minw': 20,
    'minh': 20,
    'fps': 5.0,
    'ignoreedges': False }

CHILDREN_PER_GEN = 20
MAX_GEN = 100

class TunerNotifier( object ):

    def __init__( self ):
        self.capturers = []
        self.score = 0
        self.movement_additive = 0

    def notify( self, action, sz_coords, snapshot ):
        if 'movement' == action:
            self.score += self.movement_additive

def test_sequence( seq, params, notifier, movement_additive ):
    detector = MotionDetector( **params )
    detector.cam = notifier
    notifier.movement_additive = movement_additive

    for path in seq:
        frame = cv2.imread( path )
        detector.detect( frame )

def tune( config, gen=0 ):

    logger = logging.getLogger( 'tuning' )

    if gen > MAX_GEN:
        return config

    children = []
    highest_gc = None
    for i in range( CHILDREN_PER_GEN ):
        child = config.copy()
        child['child_index'] = i
        for key in child:
            if 'child_index' == key or \
            'score' == key or \
            'fps' == key or \
            'minh' == key or \
            'minw' == key:
                continue

            if isinstance( child[key], float ):
                addition = random.random() % 5.0
                if random.randrange( 0, 10 ) > 5 and \
                0 < (child[key] - addition):
                    addition *= -1
                logger.debug( 'child %d: prop %s: adding %f to current %f',
                    i, key, addition, child[key] )
                child[key] += addition
            elif isinstance( child[key], int ):
                addition = random.randrange( -10, 10 )
                if 0 > (child[key] + addition):
                    addition *= -1
                logger.debug( 'child %d: prop %s: adding %d to current %d',
                    i, key, addition, child[key] )
                child[key] += addition

        notifier = TunerNotifier()
        test_sequence( shadow_seq, initial_config, notifier, -1 )
        test_sequence( person_seq, initial_config, notifier, 1 )
        child['score'] = notifier.score

        logger.debug( 'gen %d child %d: score %d',
            gen, child['child_index'], child['score'] )

        inserted = False
        for j in range( len( children ) ):
            if child['score'] < children[j]['score']:
                children.insert( j, child )
                inserted = True
                break
        if not inserted:
            children.append( child )

        grandchildren = []
        for j in range( int( len( children ) / 2 ) ):
            k = int( (len( children ) / 2) + j )
            grandchildren.append( tune( children[k], gen + 1 ) )

        for gc in grandchildren:
            if not highest_gc or gc['score'] > highest_gc['score']:
                highest_gc = gc

    return highest_gc

def main():
    logging.basicConfig( level=logging.DEBUG )

    print( tune( initial_config ) )

if '__main__' == __name__:
    main()
