

CAPTURE_NONE = 0
CAPTURE_VIDEO = 1
CAPTURE_PHOTO = 2

class DetectionEvent( object ):

    ''' Simple structure describing movement or activity in a frame. '''

    def __init__( self, event_type, dimensions, position, frame ):
        self.event_type = event_type
        self.dimensions = dimensions
        self.position = position
        self.frame = frame

class Detector( object ):

    ''' A detector analyses the images it's given for activity and then
    returns the results. The next step the program takes is contingent
    on these analyses, so the detection runs in the main loop. This class
    should be subclassed by specialized detectors that use various means to
    determine activity in an image. '''

    def detect( self, frame ):

        ''' Process a given frame against current object state to determine
        if movement or other activity has occurred. Return a DetectionEvent
        object describing the result. '''

        return DetectionEvent(
            'ignored', (0, 0), (0, 0), None )
