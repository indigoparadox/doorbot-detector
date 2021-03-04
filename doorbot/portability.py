
import numpy
try:
    from cv2 import cv2
except ImportError:
    import cv2

def image_to_jpeg( frame ):
    ret, jpg = cv2.imencode( '.jpg', frame )
    if ret:
        return jpg.tobytes()
    else:
        return {}

def is_frame( frame ):
    return isinstance( frame, numpy.ndarray )
