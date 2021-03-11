
import sys
import logging
from logging.handlers import SysLogHandler
from urllib.parse import urlparse

from doorbot.notifiers import Notifier

class LoggerNotifier( Notifier ):
    def __init__( self, **kwargs ):

        super().__init__( **kwargs )

        self.logger = logging.getLogger( 'notification' )

        self.logger.propagate = False

        if 'logfile' in kwargs:
            file_mode = kwargs['logmode'] if 'logmode' in kwargs else 'a'
            file_handler = logging.FileHandler( kwargs['logfile'], file_mode )
            self.logger.addHandler( file_handler )

        if 'logstream' not in kwargs or 'disabled' != kwargs['logstream']:
            stream_handler = logging.StreamHandler( sys.stdout )
            self.logger.addHandler( stream_handler )

        if 'sysloghost' in kwargs:
            syslog_url = urlparse( kwargs['sysloghost'] )
            syslog_facility = syslog_url.path[1:] if \
                syslog_url.path and 1 < len( syslog_url.path ) else \
                'user'
            syslog_port = syslog_url.port if syslog_url.port else 514
            syslog_handler = SysLogHandler(
                (syslog_url.hostname, syslog_port), syslog_facility )
            self.logger.addHandler( syslog_handler )

    def send( self, subject, message ):
        if 'ignored' == subject:
            self.logger.debug( '%s: %s', subject, message )
        else:
            self.logger.info( '%s: %s', subject, message )

PLUGIN_TYPE = 'notifiers'
PLUGIN_CLASS = LoggerNotifier
