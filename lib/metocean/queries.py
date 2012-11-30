
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

import hashlib

import metocean.prefixes as prefixes


def make_hash(pred_obj, omitted=[]):
    ''' create an md5 hash from the pred_obj (object list) dictionary
    skip any 'ommited' (list) predicates and objects'''
    pre = prefixes.Prefixes()

    
    mmd5 = hashlib.md5()
    
    for pred in pred_obj.keys():
        if pred not in omitted:
            pred_elems = pred.split(':')
            if len(pred_elems) == 2:
                if pre.prefixd.has_key(pred_elems[0]):
                    predicate = '%s%s' % (pre.prefixd[pred_elems[0]], pred_elems[1])
                else raise ValueError('predicate not in prefixes.py')
            else:
                raise ValueError('make hash passed a predicate which is not of the form <prefix>:<item>')
                                      
            if pred_obj[pred] is list:
                for obj in pred_obj[pred]:
                    mmd5.update(pred)
                    mmd5.update(obj)
            else:
                mmd5.update(pred)
                mmd5.update(po_dict[pred])
    md5 = str(mmd5.hexdigest())
    return md5
    

def revert_cache(fuseki_process, graph, debug=False):
    '''
    update a graph in the triple database removing all shards flagged with the saveCache predicate
    '''
    qstr = '''
    DELETE
    {  GRAPH <%s>
        {
        ?s ?p ?o .
        }
    }
    WHERE
    {  GRAPH <%s>
        {
        ?s ?p ?o ;
        mr:saveCache "True" .
        }
    } 
    ''' % (graph,graph)
    results = fuseki_process.run_query(qstr, update=True, debug=debug)
    return results


def save_cache(fuseki_process, graph, debug=False):
    '''
    export new records from a graph in the triple store to an external location,
    as flagged by the manager application
    clear the 'not saved' flags on records, updating a graph in the triple store
    with the fact that changes have been persisted to ttl
    '''
    qstr = '''
    CONSTRUCT
    {
        ?s ?p ?o .
    }
    WHERE
    {
    GRAPH <%s>
    {
    ?s ?p ?o ;
        mr:saveCache "True" .
    }
    } 
    ''' % graph
    results = run_query(qstr, output="text", debug=debug)
    qstr = '''
    DELETE
    {  GRAPH <%s>
        {
        ?s mr:saveCache "True" .
        }
    }
    WHERE
    {  GRAPH <%s>
        {
    ?s ?p ?o ;
        mr:saveCache "True" .
        }
    } 
    ''' % (graph,graph)
    not_results = run_query(qstr, update=True, debug=debug)
    return results


def query_cache(fuseki_process, graph, debug=False):
    '''
    return all triples cached for saving but not saved
    '''
    qstr = '''
    SELECT ?s ?p ?o
    WHERE
    {  GRAPH <%s>
        {
    ?s ?p ?o ;
        mr:saveCache "True" .
        }
    } 
    ''' % (graph)
    results = run_query(qstr, debug=debug)
    return results


def current_mappings(fuseki_process, debug=False):
    '''
    return all triples currently valid in the mappings graph
    '''
    qstr = '''
    SELECT ?s ?p ?o
    WHERE
    { GRAPH <http://metocean/mappings.ttl> {
    ?s ?p ?o ;
        mr:status ?status.
        FILTER (?status NOT IN ("Deprecated", "Broken")) .
        {
          SELECT ?map ?replaces
          WHERE
          {
           ?map mr:replaces ?replaces .

           MINUS {?map ^mr:replaces+ ?map}
           }
        }
    }
    '''
    results = fuseki_process.run_query(qstr, update=True, debug=debug)
    return results

def mapping_by_link(fuseki_process, paramlist=False,debug=False):
    '''
    return all the valid mappings, with linkage and cf elements for a given data format and linklist, 
    or all mappings if linklist is left as False 
    '''
    linkpattern = ''
    if paramlist:
        linkpattern = '''          ?link '''
        for param in paramlist:
            linkpattern += '''
                    mr:%slink <%s> ;
            ''' % (param[0].upper(),param[1])
        linkpattern.rstrip(';')
        linkpattern += ' .'
    qstr = '''
    SELECT ?map
       (GROUP_CONCAT(DISTINCT(?owner); SEPARATOR = ",") AS ?owners)
       (GROUP_CONCAT(DISTINCT(?watcher); SEPARATOR = ",") AS ?watchers) 
       ?creator 
       ?creation 
       ?status 
       ?replaces
       ?comment
       ?reason
       ?link
       (GROUP_CONCAT(DISTINCT(?cfitem); SEPARATOR = "&") AS ?cfelems) 
       (GROUP_CONCAT(DISTINCT(?cflink); SEPARATOR = "&") AS ?cflinks) 
       (GROUP_CONCAT(DISTINCT(?umlink); SEPARATOR = "&") AS ?umlinks)
       (GROUP_CONCAT(DISTINCT(?griblink); SEPARATOR = "&") AS ?griblinks)
       WHERE
       {
              GRAPH <http://metocean/cflinks.ttl> {
              ?cflink ?cfp ?cfo .
              BIND(CONCAT(STR(?cfp), ";", STR(?cfo)) AS ?cfitem)
              }
       { SELECT ?map ?owner ?watcher ?creator ?creation ?status ?replaces ?comment ?reason ?link ?cflink ?umlink ?griblink

       WHERE { GRAPH <http://metocean/mappings.ttl> {
           ?map mr:owner ?owner ;
                mr:watcher ?watcher ;
                mr:creator ?creator ;
                mr:creation ?creation ;
                mr:status ?status ;
                mr:replaces ?replaces ;
                mr:comment ?comment ;
                mr:reason ?reason ;
                mr:linkage ?link .

       FILTER (?status NOT IN ("Deprecated", "Broken"))
       MINUS {?map ^mr:replaces+ ?map}
       } GRAPH <http://metocean/linkages.ttl> {
%s
       OPTIONAL
           {?link mr:CFlink ?cflink . }
       OPTIONAL
           {?link mr:UMlink ?umlink . }
       OPTIONAL
           {?link mr:GRIBlink ?griblink .}
       

    } } } }
    GROUP BY ?map ?creator ?creation ?status ?replaces ?comment ?reason ?link
    ''' % (linkpattern)
    results = fuseki_process.run_query(qstr, debug=debug)
    return results

def fast_mapping_by_link(fuseki_process, dataformat,linklist=False,debug=False):
    '''
    return all the valid mappings, with linkage and cf elements for a given data format and linklist, 
    or all mappings if linklist is left as False 
    '''
    linkpattern = ''
    if linklist:
        linkpattern = '''          ?link '''
        for link in linklist:
            linkpattern += '''
                    mr:%slink <%s> ;
            ''' % (dataformat.upper(),link)
        linkpattern.rstrip(';')
        linkpattern += ' .'
    qstr = '''
    SELECT ?map
       (GROUP_CONCAT(DISTINCT(?owner); SEPARATOR = ",") AS ?owners)
       (GROUP_CONCAT(DISTINCT(?watcher); SEPARATOR = ",") AS ?watchers) 
       ?creator 
       ?creation 
       ?status 
       ?replaces
       ?comment
       ?reason
       ?link
       (GROUP_CONCAT(DISTINCT(?cflink); SEPARATOR = "&") AS ?cflinks) 
       (GROUP_CONCAT(DISTINCT(?umlink); SEPARATOR = "&") AS ?umlinks)
       (GROUP_CONCAT(DISTINCT(?griblink); SEPARATOR = "&") AS ?griblinks)


    WHERE
      
 { GRAPH <http://mappings/mappings.ttl> {
           ?map mr:owner ?owner ;
                mr:watcher ?watcher ;
                mr:creator ?creator ;
                mr:creation ?creation ;
                mr:status ?status ;
                mr:replaces ?replaces ;
                mr:comment ?comment ;
                mr:reason ?reason ;
                mr:linkage ?link .
%s
       FILTER (?status NOT IN ("Deprecated", "Broken"))
       MINUS {?map ^mr:replaces+ ?map}
           }
GRAPH <http://mappings/linkages.ttl> {
       OPTIONAL
           {?link mr:CFlink ?cflink .         
           }
       OPTIONAL
           {?link mr:UMlink ?umlink . }
       OPTIONAL
           {?link mr:GRIBlink ?griblink .}
       

    }}
    GROUP BY ?map ?creator ?creation ?status ?replaces ?comment ?reason ?link
    ''' % (linkpattern)
    results = fuseki_process.run_query(qstr, debug=debug)
    return results




def select_graph(fuseki_process, graph, debug=False):
    '''
    selects a particular graph from the TDB
    '''
    qstr = '''
        SELECT DISTINCT ?g
        WHERE {
            GRAPH ?g { ?s ?p ?o } .
            FILTER( REGEX(str(?g), '%s') ) .
        }

    ''' % graph
    results = fuseki_process.run_query(qstr, debug=debug)
    return results


def counts_by_graph(fuseki_process, graph, debug=False):
    '''This query relies on a feature of Jena that is not yet in the official
    SPARQL v1.1 standard insofar as 'GRAPH ?g' has undetermined behaviour
    under the standard but Jena interprets and treats the '?g' 
    just like any other variable.
    '''
    qstr = '''
        SELECT ?g (COUNT(DISTINCT ?s) as ?count)
        WHERE {
            GRAPH ?g { ?s ?p ?o } .
            FILTER( REGEX(str(?g), '%s') ) .
        }
        GROUP by ?g
        ORDER by ?g
    ''' % graph
    results = fuseki_process.run_query(qstr)
    return results

def count_by_graph(fuseki_process, debug=False):
    '''This query relies on a feature of Jena that is not yet in the official
    SPARQL v1.1 standard insofar as 'GRAPH ?g' has undetermined behaviour
    under the standard but Jena interprets and treats the '?g' 
    just like any other variable.
    '''
    qstr = '''
        SELECT ?g (COUNT(DISTINCT ?s) as ?count)
        WHERE {
            GRAPH ?g { ?s ?p ?o } .
        }
        GROUP by ?g
        ORDER by ?g
    '''
    results = fuseki_process.run_query(qstr)
    return results



def subject_by_graph(fuseki_process, graph, debug=False):
    '''
    selects distinct subject from a particular graph
    '''
    qstr = '''
        SELECT DISTINCT ?subject
        WHERE {
            GRAPH <%s> { ?subject ?p ?o } .
        }
        ORDER BY ?subject

    ''' % graph
    
    results = fuseki_process.run_query(qstr, debug=debug)
    return results

def subject_graph_pattern(fuseki_process, graph,pattern,debug=False):
    '''
    selects distinct subject from a particular graph matching a pattern
    '''
    qstr = '''
        SELECT DISTINCT ?subject
        WHERE {
            GRAPH <%s> { ?subject ?p ?o } .
            FILTER( REGEX(str(?subject), '%s') ) .            
        }
        ORDER BY ?subject

    ''' % (graph,pattern)

    results = fuseki_process.run_query(qstr, debug=debug)
    return results


def get_cflink_by_id(fuseki_process, cflink, debug=False):
    '''
    return a cflink record, if one exists, using the MD5 ID
    '''
    qstr = '''
    SELECT ?type ?standard_name ?units ?long_name
    WHERE
    { GRAPH <http://metocean/cflinks.ttl> {
    ?s mrcf:type ?type .
    OPTIONAL
    { ?s mrcf:standard_name ?standard_name .}
    OPTIONAL
    { ?s mrcf:units ?units . }
    OPTIONAL
    { ?s mrcf:long_name ?long_name . }
    FILTER (?s = <%s>)
    }
    }
    ''' % cflink
    results = fuseki_process.run_query(qstr, debug=debug)

    return results

def get_cflinks(fuseki_process, pred_obj=None, debug=False):
    '''
    return cflink records matching the predicate object dictionary items
    '''
    filterstr = ''
    if pred_obj:
        for key in pred_obj.keys():
            filterstr += '''FILTER (bound(?%s))
            FILTER (regex(str(?%s), str(%s), "i"))
            ''' % (key.split(':')[1],key.split(':')[1],pred_obj[key])
    qstr  = '''
    SELECT ?s ?type ?standard_name ?units ?long_name
    WHERE
    { GRAPH <http://metocean/cflinks.ttl> {
    ?s mrcf:type ?type .
    OPTIONAL
    { ?s mrcf:standard_name ?standard_name .}
    OPTIONAL
    { ?s mrcf:units ?units . }
    OPTIONAL
    { ?s mrcf:long_name ?long_name . }
    %s
    } }
    ''' % filterstr 
    results = fuseki_process.run_query(qstr, debug=debug)

    return results




def create_cflink(fuseki_process, po_dict, subj_pref, debug=False):
    '''
    create a new link, using the provided predicates:objectsList dictionary, if one does not already exists.
    if one already exists, use this in preference
    subj_pref is the prefix for the subject, e.g. http://www.metarelate.net/metocean/cf, http://www.metarelate.net/metocean/linkage
    '''
    md5 = make_hash(po_dict)

    # mmd5 = hashlib.md5()
    
    # for pred in po_dict.keys():
    #     mmd5.update(pred)
    #     mmd5.update(po_dict[pred])

    # md5 = str(mmd5.hexdigest())
    #ask yourself whether you want to calculate the MD5 here and use it to test, or whether to pass the predicates and objects to SPARQL to query
    #current_link = get_by_attrs(po_dict)
    current_link = get_cflinks(fuseki_process, po_dict)
    if len(current_link) == 0:
        pred_obj = ''
        for pred in po_dict.keys():
            pattern_string = ''' %s %s ;
            ''' % (pred, po_dict[pred])
            pred_obj += pattern_string
        qstr = '''
        INSERT DATA
        { GRAPH <http://metocean/cflinks.ttl>
        { <%s/%s> %s
        mr:saveCache "True" .
        }
        }
        ''' % (subj_pref, md5, pred_obj)
        results = fuseki_process.run_query(qstr, update=True, debug=debug)
        current_link = get_cflinks(po_dict)
    return current_link


def get_linkage(fuseki_process, fso_dict, debug=False):
    '''
    return a linkage if one exists, using the full record:
        a dictionary of format strings and lists of objects.
    if one does not exist, create it
    '''
    subj_pref = 'http://www.metarelate.net/metOcean/linkage'
    search_string = ''
    for fstring in fso_dict.keys():
        for obj in fso_dict[fstring]:
            search_string += '''
            %s %s ;''' % (fstring, obj)
    if search_string != '':
        search_string += '.'
        qstr = '''
        SELECT ?linkage
            (GROUP_CONCAT(DISTINCT(?cflink); SEPARATOR = "&") AS ?cflinks) 
            (GROUP_CONCAT(DISTINCT(?umlink); SEPARATOR = "&") AS ?umlinks)
            (GROUP_CONCAT(DISTINCT(?griblink); SEPARATOR = "&") AS ?griblinks)

        WHERE
        { GRAPH <http://metocean/linkages.ttl>{
            ?linkage %s
       OPTIONAL
           {?linkage mr:CFlink ?cflink . }
       OPTIONAL
           {?linkage mr:UMlink ?umlink . }
       OPTIONAL
           {?linkage mr:GRIBlink ?griblink .}
            FILTER (regex(str(?linkage),"%s", "i"))
            }
        }
        GROUP BY ?linkage
        ''' % (search_string, subj_pref)

        results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 1 and results[0] == {}:
            pre = prefixes.Prefixes()
            md5 = make_hash(fso_dict)
            # mmd5 = hashlib.md5()
            # pred_obj = ''
            # for format,objects in fso_dict.iteritems():
            #     for obj in objects:
            #         (pre['mr'], format, obj)
            #         mmd5.update('%s%slink' % (pre['mr'], format))
            #         mmd5.update(obj)

            # md5 = str(mmd5.hexdigest())

            inststr = '''
            INSERT DATA
            { GRAPH <http://metocean/linkages.ttl>
            { <%s/%s> %s
            mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, md5, search_string.rstrip('.'))
            insert_results = fuseki_process.run_query(inststr, update=True, debug=debug)
            results = fuseki_process.run_query(qstr, debug=debug)
    else:
        results = []

    return results



def create_mapping(fuseki_process, po_dict, debug=False):
    '''
    create a new mapping record from a dictionary of predicates and lists of objects
    '''
    subj_pref = 'http://www.metarelate.net/metocean/mapping'
    results = None
    pre = prefixes.Prefixes()

    if po_dict.has_key('mr:owner') and \
        po_dict.has_key('mr:watcher') and \
        po_dict.has_key('mr:creator') and len(po_dict['creator'])==1 and \
        po_dict.has_key('mr:status') and len(po_dict['status'])==1 and \
        po_dict.has_key('dc:replaces') and len(po_dict['replaces'])==1 and \
        po_dict.has_key('mr:comment') and len(po_dict['comment'])==1 and \
        po_dict.has_key('mr:reason') and len(po_dict['reason'])==1 and \
        po_dict.has_key('mr:linkage') and len(po_dict['linkage'])==1:

        md5 = make_hash(po_dict, 'mr:creation')
        #mmd5 = hashlib.md5()

        pred_obj = ''
        for pred,objects in po_dict.iteritems():
            for obj in objects:
                pattern_string = ''' mr:%s %s ;
                ''' % (pred, obj)
                pred_obj += pattern_string
                #if pred != 'creation':
                #    mmd5.update('%s%s' % (pre['mr'], pred))
                #    mmd5.update(obj)

        #md5 = str(mmd5.hexdigest())
        # check if we already have one:
        result = subject_graph_pattern('http://mappings/',
                'http://www.metarelate.net/metocean/mapping/%s' % md5)
        if len(result) == 0:
            qstr = '''
            INSERT DATA
            { GRAPH <http://metocena/mappings.ttl>
            { <%s/%s> %s
            mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, md5, pred_obj)
            results = fuseki_process.run_query(qstr, update=True, debug=debug)
    return results


def get_contacts(fuseki_process, register, debug=False):
    '''
    return a list of contacts from the tdb which are part of the named register 
    '''
    qstr = '''
    SELECT ?s
    WHERE
    { GRAPH <http://contacts/contacts.ttl> {
        ?s iso19135:definedInRegister ?register .
           OPTIONAL{
               ?s mr:retired ?retired}
               }
    FILTER (!bound(?retired))
    FILTER (regex(str(?register),"%s", "i"))
    }
    ''' % register
    results = fuseki_process.run_query(qstr, debug=debug)
    return results

def create_contact(fuseki_process, register, contact, creation, debug=False):
    '''
    create a new contact
    '''
    qstr = '''
    INSERT DATA
    { GRAPH <http://contacts/contacts.ttl> {
    %s a mr:contact ;
    iso19135:definedInRegister %s ;
    mr:creation "%s"^^xsd:dateTime .
    } }
    ''' % (contact, register, creation)
    results = fuseki_process.run_query(qstr, debug=debug)
    return results

    
        
    

def print_records(res):
    ''' helper for command line query interpretation'''
    for r in res:
        for k,v in r.iteritems():
            print k, '  ', v

