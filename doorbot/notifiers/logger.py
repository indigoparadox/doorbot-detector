
import logging

from doorbot.notifiers import Notifier

class LoggerNotifier( Notifier ):
    def __init__( self, **kwargs ):

        super().__init__( **kwargs )

        self.logger = logging.getLogger( 'detector.run.movement' )

    def send( self, subject, message ):
        if 'ignored' == subject:
            self.logger.debug( '%s: %s', subject, message )
        else:
            self.logger.info( '%s: %s', subject, message )

PLUGIN_TYPE = 'notifiers'
PLUGIN_CLASS = LoggerNotifier
