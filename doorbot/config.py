
import os
from configparser import RawConfigParser
from importlib import import_module

class DoorbotConfig( object ):

    default_config_filename = "detector.ini"
    default_config_paths = [
        os.path.join( os.path.expanduser( '~' ),
            ".{}".format( default_config_filename) ),
        os.path.join( "/etc", default_config_filename ),
        os.path.join( '.', default_config_filename )]

    def __init__( self, config_path : str, overrides : list ):

        if not config_path:
            for path in self.default_config_paths:
                if os.path.exists( path ):
                    config_path = path
                    break

        self.parser = RawConfigParser()
        self.parser.read( config_path )

        self._config = {
            'observers': [],
            'cameras': [],
            'detectors': [],
            'overlays': [],
            'capturers': [],
            'notifiers': []
        }

        for section_name in self.parser.sections():
            if section_name.startswith( 'instance.' ):
                continue

            instances = []
            try:
                instances = self.parser[section_name]['instances'].split( ',' )
            except:
                continue

            for instance in instances:

                item_config = dict( self.parser.items( 'instance.{}.{}'.format(
                    section_name, instance ) ) )

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
        return self._config[key]

    def __str__( self ):
        return str( self._config )
