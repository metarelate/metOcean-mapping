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
import json
import os
import socket
import subprocess
import sys
import time
from urllib import urlencode
from urllib2 import urlopen, Request, ProxyHandler, build_opener, install_opener, URLError


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

os.environ['JENAROOT'] = JENAROOT
os.environ['FUSEKI_HOME'] = FUSEKIROOT



def process_data(jsondata):
    resultslist = []
    try:
        jdata = json.loads(jsondata)
    except (ValueError, TypeError):
        return resultslist
    vars = jdata['head']['vars']
    data = jdata['results']['bindings']
    for item in data:
        tmplist = {}
        for var in vars:
            tmpvar = item.get(var)
            if tmpvar:
                tmplist[var] = tmpvar.get('value')
        resultslist.append(tmplist)
    return resultslist




class FusekiServer(object):

    def __init__(self, port):
        self._process = None
        self._port = port
        
    def __enter__(self):
        self.start()
        return self
        
    def __exit__(self,*args):
        self.stop(save=False)
        
    def start(self):
        '''
        initialise the fuseki process, on the defined port,
        using the created TDB in root_path/metocean.
        returns a popen instance, the running fuseki server process
        '''
        if not self._check_port():
            self._process = subprocess.Popen(['nohup',
                                       FUSEKIROOT +
                                       '/fuseki-server',
                                       '--loc=%s'%TDB,
                                       '--update',
                                       '--port=%i' % self._port,
                                       '/metocean'])
            i = 0
            while not self._check_port():
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

    def status(self):
        return self._check_port()

    def _check_port(self):
        address='localhost'
        s = socket.socket() 
        #print "Attempting to connect to %s on port %s." %(address, port)
        try: 
            s.connect((address, self._port)) 
            #print "Connected to server %s on port %s." %(address, port) 
            return True 
        except socket.error, e: 
            #print "Connecting to %s on port %s failed with the following error: %s" %(address, port, e) 
            return False 




    def clean(self):
        '''
        remove all of the files supporting the tbd instance
        '''
        if self._process:
            self.stop()
        for TDBfile in glob.glob("%s*"% TDB):
            os.remove(TDBfile)


    def save(self):
        '''
        write out all saveCache flagged changes in the metocean graph,
        appending to the relevant ttl files
        remove saveCache flags after saving
        '''
        maingraph = 'metocean'
        for subgraph in glob.glob(os.path.join(STATICDATA, maingraph, '*.ttl')):
            graph = 'http://%s/%s' % (maingraph, subgraph)
            save_string = queries.save_cache(self, graph)
            with open(subgraph, 'a') as sg:
                for line in save_string:
                    if not line.startswith('@prefix'):
                        sg.write(line)
                        sg.write('\n')



    def revert(self):
        '''
        identify all cached changes in the metocean graph and remove them, reverting the TDB to the same state as the saved ttl files
        '''
        maingraph = 'metocean'
        for ingraph in glob.glob(os.path.join(STATICDATA, maingraph, '*.ttl')):
            graph = 'http://%s/%s' % (maingraph, subgraph)
            revert_string = queries.revert_cache(self, graph)




    def load(self):
        '''
        load data from all the ttl files in the STATICDATA folder into a new TDB
        '''
        self.clean()
        for ingraph in glob.glob(os.path.join(STATICDATA, '*')):
            graph = ingraph.split('/')[-1] + '/'
            for infile in glob.glob(os.path.join(ingraph, '*.ttl')):
                subgraph = infile.split('/')[-1]
                space = ' '
                loadCall = [JENAROOT + '/bin/tdbloader',
                            '--graph=http://%s%s' % (graph,subgraph), '--loc=%s'% TDB, infile]
                print space.join(loadCall)
                subprocess.check_call(loadCall)



    def run_query(self, query_string, output='json', update=False, debug=False):
        if not self.status():
            self.start()
        # use null ProxyHandler to ignore proxy for localhost access
        proxy_support = ProxyHandler({})
        opener = build_opener(proxy_support)
        install_opener(opener)
        pre = prefixes.Prefixes()
        if debug == True:
            print pre.sparql
            print query_string
        if update:
            action = 'update'
            qstr = urlencode([
                (action, "%s %s" % (pre.sparql, query_string))])
        else:
            action = 'query'
            qstr = urlencode([
                (action, "%s %s" % (pre.sparql, query_string)),
                ("output", output),
                ("stylesheet","/static/xml-to-html-links.xsl")])

        BASEURL="http://127.0.0.1:3131/metocean/%s?" % action
        data = ''
        try:
            data = opener.open(Request(BASEURL), qstr).read()
        except URLError as err:
            raise Exception("Error connection to Fuseki server on %s. server returned" % BASEURL)
        if output == "json":
            return process_data(data)
        elif output == "text":
            return data
        else:
            return data


