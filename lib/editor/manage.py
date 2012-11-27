#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

import metocean.fuseki as fu

#import app.models

if __name__ == "__main__":
    print 'running main'
    with fu.FusekiServer(port=settings.FUSEKI_PORT) as server:
        settings.fuseki_process = server
        print 'manage.py: ', settings.fuseki_process
        execute_manager(settings)

