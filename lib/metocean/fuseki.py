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

import metocean
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
    """
    A class to represent an instance of a process managing
    a triple database and a Fuseki Server
    
    """
    def __init__(self, port, host='localhost'):
        self._process = None
        self._port = port
        self._host = host

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        #print 'exiting'
        self.stop(save=False)

    def start(self):
        """
        initialise the fuseki process, on the defined port,
        using the created TDB in root_path/metocean.
        returns a popen instance, the running fuseki server process
        
        """
        if not self._check_port():
            if os.path.exists('nohup.out'):
                print 'rm nohup.out'
                os.remove('nohup.out')
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
        """
        stop the fuseki process
        """
        if save:
            self.save_cache()
        if self._process:
            print 'stopping'
            self._process.terminate()
            self._process = None
            i = 0
            while self._check_port():
                i += i
                time.sleep(0.1)
                if i > 1000:
                    raise RuntimeError('Fuseki server not shut down correctly')

    def status(self):
        """check status of instance (is it up?)"""
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
        """
        remove all of the files supporting the tbd instance

        """
        if self._process:
            self.stop()
        for TDBfile in glob.glob("%s*"% TDB):
            os.remove(TDBfile)
        return glob.glob("%s*"% TDB)

    def save(self):
        """
        write out all saveCache flagged changes in the metocean graph,
        appending to the relevant ttl files
        remove saveCache flags after saving
        
        """
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
        """
        identify all cached changes in the metocean graph
        and remove them, reverting the TDB to the same state
        as the saved ttl files
        
        """
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
        """
        load data from all the ttl files in the STATICDATA folder into a new TDB

        """
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
        """
        run the validation queries
        """
        failures = {}
        mm_string = 'The following mappings are ambiguous, providing multiple '\
                    'targets in the same format for a particular source'
        failures[mm_string] = queries.multiple_mappings(self)
        invalid_vocab = 'The following mappings contain an undeclared URI'
        failures[invalid_vocab] = queries.valid_vocab(self)
        return failures

    def run_query(self, query_string, output='json', update=False, debug=False):
        """
        run a query_string on the FusekiServer instance
        return the results
        
        """
        if not self.status():
            self.stop()
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
            ec = 'Error connection to Fuseki server on {}.\n server returned {}'
            ec = ec.format(BASEURL, err)
            raise RuntimeError(ec)
            # self.stop()
            # self.start()
            # try:
            #     trydata = opener.open(urllib2.Request(BASEURL)).read()
            # except urllib2.URLError as err2:
            #     ec += ec + '\n' + '{}'.format(err2)
            #     raise RuntimeError(ec)
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

    def _retrieve_component(self, uri, base=True):
        qcomp = queries.retrieve_component(self, uri)
        if qcomp is None:
            msg = 'Cannot retrieve URI {!r} from triple-store.'
            raise ValueError(msg.format(uri))
        for key in ['property', 'subComponent']:
            if qcomp.get(key) is None:
                qcomp[key] = []
            if isinstance(qcomp[key], basestring):
                qcomp[key] = [qcomp[key]]
        if qcomp['property']:
            properties = []
            for puri in qcomp['property']:
                qprop = queries.retrieve_property(self, puri)
                name = qprop['name']
                name = metocean.Item(name,
                                     queries.get_label(self, name))
                curi = qprop.get('component')
                if curi is not None:
                    value = self._retrieve_component(self, curi, base=False)
                else:
                    value = qprop.get('value')
                    if value is not None:
                        value = metocean.Item(value,
                                              queries.get_label(self, value))
                    op = qprop.get('operator')
                    if op is not None:
                        op = metocean.Item(op,
                                           queries.get_label(self, op))
                properties.append(metocean.Property(puri, name, value, op))
            result = metocean.PropertyComponent(uri, properties)
        if qcomp['subComponent']:
            components = []
            for curi in qcomp['subComponent']:
                components.append(self._retrieve_component(curi, base=False))
            if base:
                result = components
            else:
                result = metocean.Component(uri, components)
        if base:
            scheme = qcomp['format']
            scheme = metocean.Item(scheme, queries.get_label(self, scheme))
            result = metocean.Concept(uri, scheme, result)
        return result

    def _retrieve_value_map(self, valmap_id, inv):
        """
        returns a dictionary of valueMap information
        
        """
        if inv == '"False"':
            inv = False
        elif inv == '"True"':
            inv = True
        else:
            raise ValueError('inv = {}, not "True" or "False"'.format(inv))
        #print '_retrieve_value_map'
        value_map = {'valueMap':valmap_id, 'mr:source':{}, 'mr:target':{}}
        vm_record = queries.retrieve_valuemap(self, valmap_id)
        if inv:
            value_map['mr:source']['value'] = vm_record['target']
            value_map['mr:target']['value'] = vm_record['source']
        else:
            value_map['mr:source']['value'] = vm_record['source']
            value_map['mr:target']['value'] = vm_record['target']
        for role in ['mr:source', 'mr:target']:
            value_map[role] = self._retrieve_value(value_map[role]['value'])

        return value_map

    def _retrieve_value(self, val_id):
        """
        returns a dictionary from a val_id
        
        """
        value_dict = {'value':val_id}
        val = queries.retrieve_value(self, val_id)
        for key in val.keys():
            value_dict['mr:{}'.format(key)] = val[key]
        for sc_prop in ['mr:subject', 'mr:object']:
            pid = value_dict.get(sc_prop)
            if pid:
                prop = queries.retrieve_scoped_property(self, pid)
                if prop:
                    value_dict[sc_prop] = {}
                    for pkey in prop:
                        pv = prop[pkey]
                        value_dict[sc_prop]['mr:{}'.format(pkey)] = pv
                        if pkey == 'hasProperty':
                            pr = value_dict[sc_prop]['mr:{}'.format(pkey)]
                            aprop = queries.retrieve_property(self, pr)
                            value_dict[sc_prop]['mr:{}'.format(pkey)] = {'property':pv}
                            for p in aprop:
                                value_dict[sc_prop]['mr:{}'.format(pkey)]['mr:{}'.format(p)] = aprop[p]
                elif pid.startswith('<http://www.metarelate.net/metOcean/value/'):
                    newval = self._retrieve_value(pid)
                    value_dict[sc_prop] = newval
                else:
                    value_dict[sc_prop] = pid
        return value_dict

    def structured_mapping(self, template):
        uri = template['mapping']
        source = self._retrieve_component(template['source'])
        target = self._retrieve_component(template['target'])
        return metocean.Mapping(uri, source, target)


def process_data(jsondata):
    """ helper method to take JSON output from a query and return the results"""
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
                    # val = ['<{}>'.format(v) for v in val.split('&')]
                else:
                    try:
                        int(val)
                    except ValueError:
                        try:
                            float(val)
                        except ValueError:
                            if not val.startswith('<'):
                                val = '"{}"'.format(val)
                tmpdict[var] = val
        if tmpdict != {}:
            resultslist.append(tmpdict)
    return resultslist
