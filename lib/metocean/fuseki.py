# (C) British Crown Copyright 2011 - 2013, Met Office
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


# Configure the Apache Jena environment.
if metocean.site_config.get('jena_dir') is not None:
    os.environ['JENAROOT'] = metocean.site_config['jena_dir']
else:
    msg = 'The Apache Jena semantic web framework has not been configured ' \
        'for metOcean.'
    raise ValueError(msg)

# Configure the Apache Fuseki environment.
if metocean.site_config.get('fuseki_dir') is not None:
    os.environ['FUSEKI_HOME'] = metocean.site_config['fuseki_dir']
else:
    msg = 'The Apache Fuseki SPARQL server has not been configured ' \
        'for metOcean.'
    raise ValueError(msg)


class FusekiServer(object):
    """
    A class to represent an instance of a process managing
    an Apache Jena triple store database and Fuseki SPARQL server.
    
    """
    def __init__(self, host='localhost', test=False):

        self._jena_dir = metocean.site_config['jena_dir']
        self._fuseki_dir = metocean.site_config['fuseki_dir']

        static_key = 'static_dir'
        tdb_key = 'tdb_dir'
        if test:
            static_key = 'test_{}'.format(static_key)
            tdb_key = 'test_{}'.format(tdb_key)
        
        if metocean.site_config.get(static_key) is None:
            msg = 'The {}static data directory for the Apache Jena database' \
                'has not been configured for metOcean.'
            raise ValueError(msg.format('test ' if test else ''))
        else:
            self._static_dir = metocean.site_config[static_key]

        if metocean.site_config.get(tdb_key) is None:
            msg = 'The Apache Jena {}triple store database directory has not ' \
                'been configured for metOcean.'
            raise ValueError(msg.format('test ' if test else ''))
        else:
            self._tdb_dir = metocean.site_config[tdb_key]
        
        self._fuseki_dataset = metocean.site_config['fuseki_dataset']

        port_key = 'port'
        if test:
            port_key = 'test_{}'.format(port_key)
        self.port = metocean.site_config[port_key]

        self.host = host
        self.test = test
        self._process = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
        
    def start(self):
        """
        Initialise the Apache Fuseki SPARQL server process on the configured
        port, using the configured Apache Jena triple store database.
        
        """
        if not self.alive():
            nohup_dir = metocean.site_config['root_dir']
            if self.test:
                nohup_dir = metocean.site_config['test_dir']
            nohup_file = os.path.join(nohup_dir, 'nohup.out')
            if os.path.exists(nohup_file):
                os.remove(nohup_file)
            cwd = os.getcwd()
            os.chdir(nohup_dir)
            args = ['nohup',
                    os.path.join(self._fuseki_dir, 'fuseki-server'),
                    '--loc={}'.format(self._tdb_dir),
                    '--update',
                    '--port={}'.format(self.port),
                    self._fuseki_dataset]
            self._process = subprocess.Popen(args)
            os.chdir(cwd)
            for attempt in xrange(metocean.site_config['timeout_attempts']):
                if self.alive():
                    break
                time.sleep(metocean.site_config['timeout_sleep'])
            else:
                msg = 'The metOcean Apache Fuseki SPARQL server failed ' \
                    'to start.'
                raise RuntimeError(msg)

    def stop(self, save=False):
        """
        Shutdown the metOcean Apache Fuseki SPARQL server.

        Kwargs:
        * save:
            Save any cache results to the configured Apache Jena triple
            store database.
            
        """
        if save:
            self.save()
        if self.alive():
            pid = self._process.pid
            self._process.terminate()
            for attempt in xrange(metocean.site_config['timeout_attempts']):
                if not self.alive():
                    break
                time.sleep(metocean.site_config['timeout_sleep'])
            else:
                msg = 'The metOcean Apache Fuseki SPARQL server failed ' \
                    'to shutdown, PID={}.'
                raise RuntimeError(msg.format(pid))
                             
            self._process = None

    def restart(self):
        """
        Restart the metOcean Apache Fuseki SPARQL server.

        """
        self.stop()
        self.start()

    def alive(self):
        """
        Determine whether the Apache Fuseki SPARQL server is available
        on the configured port.

        Returns:
            Boolean.

        """
        result = False
        s = socket.socket() 
        try: 
            s.connect((self.host, self.port))
            s.close()
            result = True
        except socket.error:
            pass
        if result and self._process is None:
            msg = 'There is currently another service on port {!r}.'
            raise RuntimeError(msg.format(self.port))
        return result

    def clean(self):
        """
        Delete all of the files in the configured Apache Jena triple
        store database.

        """
        if self.alive():
            self.stop()
        files = os.path.join(self._tdb_dir, '*')
        for tdb_file in glob.glob(files):
            os.remove(tdb_file)
        return glob.glob(files)

    def save(self):
        """
        write out all saveCache flagged changes in the metocean graph,
        appending to the relevant ttl files
        remove saveCache flags after saving
        
        """
        main_graph = metocean.site_config['graph']
        files = os.path.join(self._static_dir, main_graph, '*.ttl')
        for subgraph in glob.glob(files):
            graph = 'http://%s/%s' % (main_graph, subgraph.split('/')[-1])
            save_string = queries.save_cache(self, graph)
            with open(subgraph, 'a') as sg:
                for line in save_string.splitlines():
                    if not line.startswith('@prefix'):
                        sg.write(line)
                        sg.write('\n')

    def revert(self):
        """
        identify all cached changes in the metocean graph
        and remove them, reverting the TDB to the same state
        as the saved ttl files
        
        """
        main_graph = metocean.site_config['graph']
        files = os.path.join(self._static_dir, main_graph, '*.ttl')
        for infile in glob.glob(files):
            ingraph = infile.split('/')[-1]
            graph = 'http://%s/%s' % (main_graph, ingraph)
            revert_string = queries.revert_cache(self, graph)

    def query_cache(self):
        """
        identify all cached changes in the metocean graph

        """
        results = []
        main_graph = metocean.site_config['graph']
        files = os.path.join(self._static_dir, main_graph, '*.ttl')
        for infile in glob.glob(files):
            ingraph = infile.split('/')[-1]
            graph = 'http://%s/%s' % (main_graph, ingraph)
            result = queries.query_cache(self, graph)
            results = results + result
        return results

    def load(self):
        """
        Load all the static data turtle files into the new Apache Jena
        triple store database.

        """
        self.clean()
        graphs = os.path.join(self._static_dir, '*')
        for ingraph in glob.glob(graphs):
            graph = ingraph.split('/')[-1]
            subgraphs = os.path.join(ingraph, '*.ttl')
            for insubgraph in glob.glob(subgraphs):
                subgraph = insubgraph.split('/')[-1]
                tdb_load = [os.path.join(self._jena_dir, 'bin/tdbloader'),
                            '--graph=http://{}/{}'.format(graph, subgraph),
                            '--loc={}'.format(self._tdb_dir),
                            insubgraph]
                print ' '.join(tdb_load)
                subprocess.check_call(tdb_load)

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
        if not self.alive():
            self.restart()
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
        BASEURL = "http://%s:%i%s/%s?" % (self.host, self.port,
                                          self._fuseki_dataset, action)
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

    def retrieve_mappings(self, source, target):
        """
        return the format specific mappings for a particular source
        and target format

        """
        if isinstance(source, basestring) and \
                not metocean.Item(source).is_uri():
            source = os.path.join('<http://www.metarelate.net/metOcean/format',
                                  '{}>'.format(source.lower()))
        if isinstance(target, basestring) and \
                not metocean.Item(target).is_uri():
            target = os.path.join('<http://www.metarelate.net/metOcean/format',
                                  '{}>'.format(target.lower()))
        mappings = queries.valid_ordered_mappings(self, source, target)
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
                    value = self._retrieve_component(curi, base=False)
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
