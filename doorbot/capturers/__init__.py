
import logging
import os
import shutil
from datetime import datetime
from threading import Thread

class Capture( object ):

    ''' Abstract module for capturing and storing frames for archival. '''

    def __init__( self, **kwargs ):

        self.path = kwargs['path'] if 'path' in kwargs else '/tmp'
        self.backup_path = \
            kwargs['backuppath'] if 'backuppath' in kwargs else '/tmp'
        self.ts_format = kwargs['tsformat'] if 'tsformat' in kwargs else \
            '%Y-%m-%d-%H-%M-%S-%f'

    def handle_motion_frame( self, frame, width, height ):

        ''' Append a frame to the current animation, or handle it
        individually. '''

        raise Exception( 'not implemented!' )

    def finalize_motion( self, frame, width, height ):

        ''' Process the batch of recent motion frames into e.g. a video. '''

        raise Exception( 'not implemented!' )
