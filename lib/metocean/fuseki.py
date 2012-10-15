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

import os
import sys
import glob
import subprocess

import metocean.queries as queries

home = '/net/home/h04/itmh/'

root_path = '%smetarelate/metOcean-mapping' % home

jenaroot = '%sjena/apache-jena-2.7.3' % home
fusekiroot = '%sjena/jena-fuseki-0.2.4' % home
fport = 3131

os.environ['JENAROOT'] = jenaroot
os.environ['FUSEKI_HOME'] = fusekiroot


def FileHash(file):
    '''large file md5 hash generation'''
    md5 = hashlib.md5()
    with open(file,'rb') as f: 
        for chunk in iter(lambda: f.read(8192), b''): 
             md5.update(chunk)
    return md5.hexdigest()



def load():
    '''
    load data from all the ttl files in the staticData folder into a new tdb
    '''
    clean()
    for ingraph in glob.glob(root_path + '/staticData/*'):
        #print ingraph
        graph = ingraph.split('/')[-1] + '/'
        for infile in glob.glob(ingraph + '/*.ttl'):
            subgraph = ''
            if graph == 'um/':
                subgraph = infile.split('/')[-1]#.rstrip('.ttl')
            space = ' '
            loadCall = [jenaroot + '/bin/tdbloader', '--graph=http://%s%s' % (graph,subgraph), '--loc=%s/metocean_store/'% root_path, infile]
            print space.join(loadCall)
            subprocess.check_call(loadCall)



def start():
    '''
    initialise the fuseki process, using the created tdb in root_path/metocean 
    '''
    fuseki = subprocess.Popen(['nohup',
                               fusekiroot +
                               '/fuseki-server',
                               '--loc=%s/metocean_store/'%root_path,
                               '--update',
                               '--port=%s' % fport,
                               '/metocean'])
    return fuseki


def stop(fuseki, save=True):
    '''
    stop the fuseki process
    '''
    if save:
        save_cache()
    fuseki.terminate()



def clean(fuseki=None):
    '''
    remove all of the files supporting the tbd instance
    '''
    if fuseki:
        fuseki.terminate()
#    os.remove('nohup.out')
    for tdbfile in glob.glob("%s/metocean_store/*"% root_path):
        os.remove(tdbfile)



def save_cache():
    '''
    write out all saveCache flagged changes to new ttl files
    remove saveCache flags after saving
    '''
    for ingraph in glob.glob(root_path + '/staticData/*'):
        graph = ingraph.split('/')[-1]
        save_string = queries.save_cache(graph)
        clear_result = queries.clear_cache(graph)
        tfile = '%s/save_tmp.ttl' % ingraph
        temp = open(tfile, 'w')
        temp.write(save_string)
        temp.close()
        md5 = str(FileHash(tfile))
        os.rename(tfile, '%s/%s.ttl' % (ingraph,md5))

    
    
def revert_cache():
    '''
    identify all cached changes in the system and remove them, reverting the tdb to the same state as the saved ttl files
    '''
    for ingraph in glob.glob(root_path + '/staticData/*'):
        graph = ingraph.split('/')[-1]
        revert_string = queries.revert_cache(graph)
    
