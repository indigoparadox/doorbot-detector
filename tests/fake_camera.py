
import random
import tempfile
import shutil
from contextlib import contextmanager

import numpy
try:
    from cv2 import cv2
except ImportError:
    import cv2

from faker.providers import BaseProvider

class FakeCamera( BaseProvider ):

    def random_image( self, width, height ):

        image_out = numpy.random.randint(
            255, size=( width, height, 3), dtype=numpy.uint8 )

        return image_out

    def frame_rect( self, detector_config ):

        frame_width = int( detector_config['width'] )
        frame_height = int( detector_config['height'] )

        rect_w = random.randint(
            int( detector_config['minw'] ), frame_width )
        rect_h = random.randint(
            int( detector_config['minh'] ), frame_height )
        rect_x = random.randint( 0, frame_width - rect_w )
        rect_y = random.randint( 0, frame_height - rect_h )

        return (rect_x, rect_y, rect_w, rect_h)

    @contextmanager
    def directory( self ):
        temp_dir_path = None
        try:
            temp_dir_path = tempfile.mkdtemp()
            yield temp_dir_path
        finally:
            shutil.rmtree( temp_dir_path )
