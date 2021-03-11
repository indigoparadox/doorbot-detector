
import os
from configparser import RawConfigParser
from importlib import import_module

class DoorbotConfig( object ):

    default_config_filename = "detector.ini"
    default_config_paths = [
        os.path.join( os.path.expanduser( '~' ),
            ".{}".format( default_config_filename) ),
        os.path.join( "/etc", default_config_filename )]

    def __init__( self, config_path : str, overrides : list ):

        if not config_path:
            for path in self.default_config_paths:
                if os.path.exists( path ):
                    config_path = path
                    break

        config = RawConfigParser()
        config.read( config_path )

        self._config = {
            'observers': [],
            'cameras': [],
            'detectors': [],
            'overlays': [],
            'capturers': [],
            'notifiers': []
        }

        for section_name in config.sections():
            item_config = dict( config.items( section_name ) )

            # Apply any applicable overrides.
            for override_section, override_option, override_value in overrides:
                if section_name == override_section:
                    item_config[override_option] = override_value

            if 'enable' in item_config and 'true' == item_config['enable']:
                item_config['module'] = import_module( section_name.strip() )

                # Import module and stow config.
                item_config['type'] = item_config['module'].PLUGIN_TYPE
                self._config[item_config['type']].append( item_config )


    def __getitem__( self, key : str ):
        return dict( self._config.items( key ) )

    def __str__( self ):
        return str( self._config )
