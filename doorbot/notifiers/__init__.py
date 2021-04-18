
import logging

class Notifier( object ):

    def __init__( self, instance_name, **kwargs ):
        self.kwargs = kwargs
        self.camera_key = kwargs['camera']
        self.instance_name = instance_name

    def send( self, subject, message ):
        pass

    def snapshot( self, subject, attachment ):
        pass
