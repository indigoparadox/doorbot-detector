
import logging

class Notifier( object ):

    def __init__( self, **kwargs ):
        self.kwargs = kwargs

    def send( self, subject, message ):
        pass

    def snapshot( self, subject, attachment ):
        pass
