
import logging

class Notifier( object ):

    def __init__( self, **kwargs ):
        self.kwargs = kwargs
        self.camera_key = kwargs['camera']

    def send( self, subject, message ):
        pass

    def snapshot( self, subject, attachment ):
        pass
