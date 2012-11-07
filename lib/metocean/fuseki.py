# (C) British Crown Copyright 2011 - 2012, Met Office
# 
# This file is part of metOcean-mapping.
# 
# metOcean-mapping is free software: you can redistribute it and/or 
# modify it under the terms of the GNU Lesser General Public License 
# as published by the Free Software Foundation, either version 3 of 
# the License, or (at your option) any later version.
# 
# metOcean-mapping is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with metOcean-mapping. If not, see <http://www.gnu.org/licenses/>.


import ConfigParser
import glob
import os
import socket
import subprocess
import sys
import time

import metocean.prefixes as prefixes
import metocean.queries as queries

# configure paths for the data, triple database and jena install
ROOT_PATH = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(ROOT_PATH, 'etc')
parser = ConfigParser.SafeConfigParser()
parser.read(os.path.join(CONFIG_PATH,'metocean.config'))

STATICDATA = parser.get('metocean','staticData')
TDB = parser.get('metocean','TDB')
JENAROOT = parser.get('metocean','jenaroot')
FUSEKIROOT = parser.get('metocean','fusekiroot')
FUSEKIPORT = int(parser.get('metocean','port'))

os.environ['JENAROOT'] = JENAROOT
os.environ['FUSEKI_HOME'] = FUSEKIROOT


def filehash(file):
    '''large file md5 hash generation'''
    md5 = hashlib.md5()
    with open(file,'rb') as f: 
        for chunk in iter(lambda: f.read(8192), b''): 
             md5.update(chunk)
    return md5.hexdigest()


def check_port(address='localhost', port=FUSEKIPORT):
    s = socket.socket() 
    #print "Attempting to connect to %s on port %s." %(address, port)
    try: 
        s.connect((address, port)) 
        #print "Connected to server %s on port %s." %(address, port) 
        return True 
    except socket.error, e: 
        #print "Connecting to %s on port %s failed with the following error: %s" %(address, port, e) 
        return False 

class FusekiServer(object):

    def __init__(self):
        self._process = None
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self,*args):
        self.stop(save=False)
        
    def start(self, port=FUSEKIPORT):
        '''
        initialise the fuseki process, on the defined port,
        using the created TDB in root_path/metocean.
        returns a popen instance, the running fuseki server process
        '''
        if not check_port(port=port):
            self._process = subprocess.Popen(['nohup',
                                       FUSEKIROOT +
                                       '/fuseki-server',
                                       '--loc=%s'%TDB,
                                       '--update',
                                       '--port=%i' % port,
                                       '/metocean'])
            i = 0
            while not check_port(port=port):
                i+=1
                time.sleep(0.1)
                if i > 1000:
                    raise RuntimeError('Fuseki server not started up correctly')



    def stop(self, save=False):
        '''
        stop the fuseki process
        '''
        if save:
            self.save_cache()
        if self._process:
            self._process.terminate()



    def clean(self):
        '''
        remove all of the files supporting the tbd instance
        '''
        if self._process:
            self.stop()
        for TDBfile in glob.glob("%s*"% TDB):
            os.remove(TDBfile)


    def save_cache(self):
        '''
        write out all saveCache flagged changes to new ttl files
        remove saveCache flags after saving
        '''
        for ingraph in glob.glob(os.path.join(STATICDATA, '*')):
            graph = ingraph.split('/')[-1]
            save_string = queries.save_cache(graph)
            clear_result = queries.clear_cache(graph)
            tfile = tempfile.mkstemp()#'%s/save_tmp.ttl' % ingraph
            with open(tfile, 'w') as temp:
                temp.write(save_string)
            md5 = str(filehash(tfile))
            os.rename(tfile, '%s/%s.ttl' % (ingraph,md5))


    def revert_cache(self):
        '''
        identify all cached changes in the system and remove them, reverting the TDB to the same state as the saved ttl files
        '''
        for ingraph in glob.glob(os.path.join(STATICDATA, '*')):
            graph = ingraph.split('/')[-1]
            revert_string = queries.revert_cache(graph)





    def load(self):
        '''
        load data from all the ttl files in the STATICDATA folder into a new TDB
        '''
        self.clean()
        for ingraph in glob.glob(os.path.join(STATICDATA, '*')):
            #print ingraph
            graph = ingraph.split('/')[-1] + '/'
            for infile in glob.glob(os.path.join(ingraph, '*.ttl')):
                subgraph = ''
                if graph == 'um/':
                    subgraph = infile.split('/')[-1]#.rstrip('.ttl')
                space = ' '
                loadCall = [JENAROOT + '/bin/tdbloader',
                            '--graph=http://%s%s' % (graph,subgraph), '--loc=%s'% TDB, infile]
                print space.join(loadCall)
                subprocess.check_call(loadCall)



