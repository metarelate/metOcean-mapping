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
import urllib
import urllib2

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
DATASET = '/metocean'

os.environ['JENAROOT'] = JENAROOT
os.environ['FUSEKI_HOME'] = FUSEKIROOT






class FusekiServer(object):
    '''
    A class to represent an instance of a process managing
    a triple database and a Fuseki Server
    '''
    def __init__(self, port, host='localhost'):
        self._process = None
        self._port = port
        self._host = host
        
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
        # import pdb
        # pdb.set_trace()
        if not self._check_port():
            self._process = subprocess.Popen(['nohup',
                                       FUSEKIROOT +
                                       '/fuseki-server',
                                       '--loc=%s'%TDB,
                                       '--update',
                                       '--port=%i' % self._port,
                                       DATASET])
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
            print 'stopping'
            self._process.terminate()
            self._process = None
            print 'stop', self._process

    def status(self):
        return self._check_port()

    def _check_port(self):
        s = socket.socket() 
        #print "Attempting to connect to %s on port %s." %(address, port)
        try: 
            s.connect((self._host, self._port)) 
            #print "Connected to server %s on port %s." %(address, port) 
            return True 
        except socket.error, e: 
            #print "Connecting to %s on port %s failed with
            # the following error: %s" %(address, port, e) 
            return False 




    def clean(self):
        '''
        remove all of the files supporting the tbd instance
        '''
        print 'cleaning'
        print self._process
#        if self._process:
        self.stop()
        for TDBfile in glob.glob("%s*"% TDB):
            os.remove(TDBfile)
        return glob.glob("%s*"% TDB)
        


    def save(self):
        '''
        write out all saveCache flagged changes in the metocean graph,
        appending to the relevant ttl files
        remove saveCache flags after saving
        '''
        maingraph = 'metarelate.net'
        for subgraph in glob.glob(os.path.join(STATICDATA, maingraph, '*.ttl')):
            graph = 'http://%s/%s' % (maingraph, subgraph.split('/')[-1])
            save_string = queries.save_cache(self, graph)
            with open(subgraph, 'a') as sg:
                for line in save_string.splitlines():
                    if not line.startswith('@prefix'):
                        #print 'writing', line
                        sg.write(line)
                        sg.write('\n')



    def revert(self):
        '''
        identify all cached changes in the metocean graph
        and remove them, reverting the TDB to the same state
        as the saved ttl files
        '''
        maingraph = 'metarelate.net'
        for infile in glob.glob(os.path.join(STATICDATA, maingraph, '*.ttl')):
            ingraph = infile.split('/')[-1]
            graph = 'http://%s/%s' % (maingraph, ingraph)
            revert_string = queries.revert_cache(self, graph)

    def query_cache(self):
        """
        identify all cached changes in the metocean graph
        """
        results = []
        maingraph = 'metarelate.net'
        for infile in glob.glob(os.path.join(STATICDATA, maingraph, '*.ttl')):
            ingraph = infile.split('/')[-1]
            graph = 'http://%s/%s' % (maingraph, ingraph)
            result = queries.query_cache(self, graph)
            results = results + result
        return results




    def load(self):
        '''
        load data from all the ttl files in the STATICDATA folder into a new TDB
        '''
        print 'clean:'
        self.clean()
        for ingraph in glob.glob(os.path.join(STATICDATA, '*')):
            graph = ingraph.split('/')[-1] + '/'
            for infile in glob.glob(os.path.join(ingraph, '*.ttl')):
                subgraph = infile.split('/')[-1]
                space = ' '
                loadCall = [JENAROOT + '/bin/tdbloader',
                            '--graph=http://%s%s' % (graph,subgraph),
                            '--loc=%s'% TDB, infile]
                print space.join(loadCall)
                subprocess.check_call(loadCall)


    def validate(self):
        """run the validation queries"""
        failures = {}
        mm_string = 'The following mappings are ambiguous, providing multiple'
        mm_string += ' targets in the same format for a particular source'
        failures[mm_string] = queries.multiple_mappings(self)
        return failures




    def run_query(self, query_string, output='json', update=False, debug=False):
        '''run a query_string on the FusekiServer instance
        '''
        if not self.status():
            self.start()
        # use null ProxyHandler to ignore proxy for localhost access
        proxy_support = urllib2.ProxyHandler({})
        opener = urllib2.build_opener(proxy_support)
        urllib2.install_opener(opener)
        pre = prefixes.Prefixes()
        if debug == True:
            k=0
            for j, line in enumerate(pre.sparql.split('\n')):
                print j,line
                k+=1
            for i, line in enumerate(query_string.split('\n')):
                print i+k, line
        if update:
            action = 'update'
            qstr = urllib.urlencode([
                (action, "%s %s" % (pre.sparql, query_string))])
        else:
            action = 'query'
            qstr = urllib.urlencode([
                (action, "%s %s" % (pre.sparql, query_string)),
                ("output", output),
                ("stylesheet","/static/xml-to-html-links.xsl")])
        BASEURL = "http://%s:%i%s/%s?" % (self._host, self._port,
                                          DATASET, action)
        data = ''
        try:
            data = opener.open(urllib2.Request(BASEURL), qstr).read()
        except urllib2.URLError as err:
            ec = "Error connection to Fuseki server on {}.\n".format(BASEURL)
            ec += 'server returned {}'.format(err)
            raise Exception(ec)
        if output == "json":
            return process_data(data)
        elif output == "text":
            return data
        else:
            return data



    def retrieve_mappings(self, s_format, t_format):
        """
        return the format specific mappings for a particular source
        and target format
        """
        mappings = queries.valid_ordered_mappings(self, s_format, t_format)
        mapping_list = []
        for mapping in mappings:
            mapping_list.append(self.structured_mapping(mapping))
        return mapping_list

    def _retrieve_format_concept(self, fc_id):
        """
        returns a dictionary of formatConcept information
        recursive call to get all the nested formatConcept
        information from a formatConcept
        """
        # fc_dict = {'formatConcept':'', 'mr:format': '', 'skos:member': []},
        top_fc = queries.retrieve_format_concept(self, fc_id)
        if top_fc:
            fc_dict = {'formatConcept':fc_id, 'mr:format': top_fc['format'],
                       'skos:member':[]}
            if isinstance(top_fc['member'], str):
                top_fc['member'] = [top_fc['member']]
            for member in top_fc['member']:
                if member.startswith(
                        '<http://www.metarelate.net/metOcean/property/'):
                    prop_dict = queries.retrieve_property(self, member)
                    pref_prop_dict = {}
                    if prop_dict.get('name'):
                        pref_prop_dict['mr:name'] = prop_dict['name']
                    if prop_dict.get('operator'):
                        pref_prop_dict['mr:operator'] = prop_dict['operator']
                    if prop_dict.get('value'):
                        pref_prop_dict['rdf:value'] = prop_dict['value']
                    fc_dict['skos:member'].append(pref_prop_dict)
                elif member.startswith(
                        '<http://www.metarelate.net/metOcean/formatConcept/'):
                    subfc_dict = self._retrieve_format_concept(member)
                    fc_dict.append(subfc_dict)
                else:
                    raise ValueError('{} a malformed formatConcept'.format(
                                                                        fc_id))
        return fc_dict

    def _retrieve_value_map(self, valmap_id, inv):
        """
        returns a dictionary of valueMap information
        """
        if inv == "False":
            inv = False
        elif inv == "True":
            inv = True
        else:
            raise ValueError('inv = {}, not "True" or "False"'.format(inv))
        value_map = {'valueMap':valmap_id, 'mr:source':{}, 'mr:target':{}}
        vm_record = queries.retrieve_valuemap(self, valmap_id)
        if inv:
            value_map['mr:source']['source'] = vm_record['target']
            value_map['mr:target']['target'] = vm_record['source']
        else:
            value_map['mr:source']['source'] = vm_record['source']
            value_map['mr:target']['target'] = vm_record['target']
        for role in ['source','target']:
            val = queries.retrieve_value(self,
                            value_map['mr:{}'.format(role)]['{}'.format(role)])
            for key in val.keys():
                value_map['mr:{}'.format(role)]['mr:{}'.format(key)] = val[key]
            for sc_prop in ['mr:subject', 'mr:object']:
                prop = queries.retrieve_scoped_property(self,
                    value_map['mr:{}'.format(role)]['mr:{}'.format(sc_prop)])
                for pkey in prop.keys():
                    pv = prop[pkey]
                    value_map['mr:{}'.format(role)]['mr:{}'.format(pkey)] = pv
                        
        return value_map


    def structured_mapping(self, mapping):
        """
        returns the json for a mapping, fully expanded
        from the mapping Id
        """
        referrer = {'mapping': mapping['mapping'],
                    'mr:source': {'formatConcept': ''},
                    'mr:target': {'formatConcept': ''},
                    'mr:valueMap': []}
        if mapping.get('source') and mapping.get('target'):
            referrer['mr:source'] = self._retrieve_format_concept(mapping['source'])
            referrer['mr:target'] = self._retrieve_format_concept(mapping['target'])
            if mapping.get('valueMaps'):
                if isinstance(mapping['valueMaps'], string):
                    mapping['valueMaps'] = [mapping['valueMaps']]
                for valmap in mapping['valueMaps']:#.split('&'):
                    referrer['mr:valueMap'].append(self._retrieve_value_map(valmap,
                                                        mapping['inverted']))
        return referrer





def process_data(jsondata):
    '''helper method to take JSON output from a query and return the results'''
    resultslist = []
    try:
        jdata = json.loads(jsondata)
    except (ValueError, TypeError):
        return resultslist
    vars = jdata['head']['vars']
    data = jdata['results']['bindings']
    for item in data:
        tmpdict = {}
        for var in vars:
            tmpvar = item.get(var)
            if tmpvar:
                val = tmpvar.get('value')
                if str(val).startswith('http://') or \
                   str(val).startswith('https://') :
                    if len(val.split('&')) == 1:
                        val = '<{}>'.format(val)
                    else:
                        val = ['<{}>'.format(v) for v in val.split('&')]
                tmpdict[var] = val
        if tmpdict != {}:
            resultslist.append(tmpdict)
    return resultslist

# def group_by(resultslist, group_by):
#     """
#     implementation of group_by functionality as a post processing step
#     takes a resultslist, as output from process_data and uses the named group_by
#     keys to aggregate the quantities into lists
#     """
#     modresults = resultslist
#     return modresults
