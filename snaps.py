#!/usr/bin/env python3

import os
import argparse
import logging
from configparser import ConfigParser
from http.server import BaseHTTPRequestHandler, HTTPServer

STYLESHEET = '''

img {
    width: 160px;
    height: 120px;
    display: inline-block;
}

'''

class SnapHandler( BaseHTTPRequestHandler ):

    def do_GET( self ):

        safe_path = '{}{}'.format( os.getcwd(), self.path ).replace( '..', '' )

        if not os.path.exists( safe_path ):
            self.send_response( 404 )
            return

        self.send_response( 200 )

        if safe_path.endswith( '.jpg' ):
            self.send_header( 'Content-type', 'image/jpeg' )
            self.end_headers()
            with open( safe_path, 'rb' ) as path_file:
                self.wfile.write( path_file.read() )
            return

        self.send_header( 'Content-type', 'text/html' )
        self.end_headers()

        dir_entries = os.listdir( os.getcwd() )
        dir_entries.sort()
        self.wfile.write( bytes( '<!DOCTYPE html><html><head><style>', 'utf-8' ) )
        self.wfile.write( bytes( STYLESHEET, 'utf-8' ) )
        self.wfile.write( bytes( '</style></head><body>', 'utf-8' ) )
        for entry in dir_entries:
            self.wfile.write( bytes( '<img src="{}" />'.format( entry ), 'utf-8' ) )
        self.wfile.write( bytes( '</body></html>', 'utf-8' ) )

def main():
    parser = argparse.ArgumentParser()

    verbosity_grp = parser.add_mutually_exclusive_group()

    verbosity_grp.add_argument( '-v', '--verbose', action='store_true' )

    verbosity_grp.add_argument( '-q', '--quiet', action='store_true' )

    parser.add_argument( '-c', '--config', action='store' )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig( level=logging.DEBUG )
    elif args.quiet:
        logging.basicConfig( level=logging.ERROR )
    else:
        logging.basicConfig( level=logging.INFO )

    config = ConfigParser()
    config.read( args.config )
    os.chdir( config['snapserve']['path'] )
    hostname = config['snapserve']['listen'] \
        if 'listen' in config['snapserve'] else '0.0.0.0'
    port = int( config['snapserve']['port'] ) \
        if 'port' in config['snapserve'] else 8888
    server = HTTPServer( (hostname, port), SnapHandler )
    server.serve_forever()

if '__main__' == __name__:
    main()

