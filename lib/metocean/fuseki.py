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

import metocean.prefixes as prefixes
import metocean.queries as queries

# configure paths for the data, triple database and jena install
ROOT_PATH = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(ROOT_PATH, 'etc')
parser = ConfigParser.SafeConfigParser()
parser.read(os.path.join(CONFIG_PATH,'metocean.config'))

staticData = parser.get('metocean','staticData')
tdb = parser.get('metocean','tdb')
jenaroot = parser.get('metocean','jenaroot')
fusekiroot = parser.get('metocean','fusekiroot')
fport = parser.get('metocean','port')

os.environ['JENAROOT'] = jenaroot
os.environ['FUSEKI_HOME'] = fusekiroot


def filehash(file):
    '''large file md5 hash generation'''
    md5 = hashlib.md5()
    with open(file,'rb') as f: 
        for chunk in iter(lambda: f.read(8192), b''): 
             md5.update(chunk)
    return md5.hexdigest()


def check_port(address='localhost',port=int(fport)):
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
    def __enter__(self):
        print 'enter called'
        self.start()
    def __exit__(self,*args):
        print 'exit called'
        self.stop(save=False)
    def load(self):
        load()

    def start(self):
        '''
        initialise the fuseki process, using the created tdb in root_path/metocean
        returns a popen instance, the running fuseki server process
        '''
        self.server = subprocess.Popen(['nohup',
                                   fusekiroot +
                                   '/fuseki-server',
                                   '--loc=%s'%tdb,
                                   '--update',
                                   '--port=%s' % fport,
                                   '/metocean'])
        i = 0
        while not check_port():
            i+=1
            if i > 100000:
                raise RuntimeError('Fuseki server not started up correctly')
        


    def stop(self, save=False):
        '''
        stop the fuseki process
        '''
        if save:
            self.save_cache()
        if self.server:
            self.server.terminate()



    def clean(self):
        '''
        remove all of the files supporting the tbd instance
        '''
        if self.fuseki_server:
            self.stop()
        for tdbfile in glob.glob("%s*"% tdb):
            os.remove(tdbfile)


    def save_cache(self):
        '''
        write out all saveCache flagged changes to new ttl files
        remove saveCache flags after saving
        '''
        for ingraph in glob.glob('%s*' % staticData):
            graph = ingraph.split('/')[-1]
            save_string = queries.save_cache(graph)
            clear_result = queries.clear_cache(graph)
            tfile = '%s/save_tmp.ttl' % ingraph
            with open(tfile, 'w') as temp:
                temp.write(save_string)
            md5 = str(filehash(tfile))
            os.rename(tfile, '%s/%s.ttl' % (ingraph,md5))


    def revert_cache(self):
        '''
        identify all cached changes in the system and remove them, reverting the tdb to the same state as the saved ttl files
        '''
        for ingraph in glob.glob('%s*' % staticData):
            graph = ingraph.split('/')[-1]
            revert_string = queries.revert_cache(graph)





    def load(self):
        '''
        load data from all the ttl files in the staticData folder into a new tdb
        '''
        clean()
        for ingraph in glob.glob(staticData + '*'):
            #print ingraph
            graph = ingraph.split('/')[-1] + '/'
            for infile in glob.glob(ingraph + '/*.ttl'):
                subgraph = ''
                if graph == 'um/':
                    subgraph = infile.split('/')[-1]#.rstrip('.ttl')
                space = ' '
                loadCall = [jenaroot + '/bin/tdbloader', '--graph=http://%s%s' % (graph,subgraph), '--loc=%s'% tdb, infile]
                print space.join(loadCall)
                subprocess.check_call(loadCall)



