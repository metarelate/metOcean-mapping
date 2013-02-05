

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

import collections
import hashlib


import metocean.prefixes as prefixes


def make_hash(pred_obj, omitted=None):
    """ creates and returns an sha-1 hash of the elements in the pred_obj
    (object list) dictionary
    skipping any 'ommited' (list) predicates and objects

    Args:
    
    * pred_obj:
        A dictionary of predicates and lists of objects, or single objects
        which will be used, in order, to construct the hash
    * omitted:
        A list of predicate strings to be ignored when building the hash 
    """
    if omitted is None:
        omitted = []
    pre = prefixes.Prefixes()
    sha1 = hashlib.sha1()
    #sort keys
    po_keys = pred_obj.keys()
    po_keys.sort()
    for pred in po_keys:
        if pred not in omitted:
            pred_elems = pred.split(':')
            if len(pred_elems) == 2:
                if pre.has_key(pred_elems[0]):
                    predicate = '%s%s' % (pre[pred_elems[0]], pred_elems[1])
                else:
                    raise ValueError('predicate not in prefixes.py')
            else:
                raise ValueError('make hash passed a predicate '
                                 'which is not of the form <prefix>:<item>')
            if isinstance(pred_obj[pred], list):
                for obj in pred_obj[pred]:
                    sha1.update(predicate)
                    sha1.update(obj)
            else:
                sha1.update(predicate)
                sha1.update(pred_obj[pred])
    sha1_hex = str(sha1.hexdigest())
    return sha1_hex
    

def revert_cache(fuseki_process, graph, debug=False):
    """
    update a graph in the triple database removing all records
    flagged with the saveCache predicate
    """
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
    """
    export new records from a graph in the triple store to an external location,
    as flagged by the manager application
    clear the 'not saved' flags on records, updating a graph in the triple store
    with the fact that changes have been persisted to ttl
    """
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
    results = fuseki_process.run_query(qstr, output="text", debug=debug)
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
    delete_results = fuseki_process.run_query(qstr, update=True, debug=debug)
    save_string = ''
    for line in results.split('\n'):
        if not line.strip().startswith('mr:saveCache'):
            save_string += line
            save_string += '\n'
        else:
            if line.endswith('.'):
                save_string += '\t.\n'
    return save_string


def query_cache(fuseki_process, graph, debug=False):
    """
    return all triples cached for saving but not saved
    """
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
    results = fuseki_process.run_query(qstr, debug=debug)
    return results

def get_contacts(fuseki_process, register, debug=False):
    """
    return a list of contacts from the tdb which are part of the named register 
    """
    qstr = '''
    SELECT ?s
    WHERE
    { GRAPH <http://metarelate.net/contacts.ttl> {
        ?s skos:member ?register .
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
    """
    create a new contact
    """
    qstr = '''
    INSERT DATA
    { GRAPH <http://metarelate.net/contacts.ttl> {
    %s a mr:contact ;
    iso19135:definedInRegister %s ;
    mr:creation "%s"^^xsd:dateTime .
    } }
    ''' % (contact, register, creation)
    results = fuseki_process.run_query(qstr, update=True, debug=debug)
    return results

def create_mediator(fuseki_process, label, fformat, debug=False):
    """
    create a new mediator
    """
    ff = fformat.rstrip('}').split('/')[-1]
    med = '<http://www.metarelate.net/metocean/mediates/{}/{}>'.format(ff,
                                                                       label)
    qstr = '''
    INSERT DATA
    { GRAPH <http://metarelate.net/concepts.ttl> {
    %s a skos:Concept ;
         skos:label %s
         mr:format %s .
         } }
    ''' % (med, label, fformat)
    results = fuseki_process.run_query(qstr, update=True, debug=debug)
    return results

def get_mediators(fuseki_process, debug=False):
    """
    return all mediators from the triple store
    """
    qstr = '''
    SELECT ?mediator ?format ?label
    WHERE
    { GRAPH <http://metarelate.net/contacts.ttl> {
        ?mediator mr:format ?format ;
                  skos:label ?label .
    FILTER(regex(str(?mediator),"http://www.metarelate.net/metocean/mediates/"))
    }
    ''' 
    results = fuseki_process.run_query(qstr, debug=debug)
    return results
    


def print_records(res):
    """ helper for command line query interpretation"""
    print_string = ''
    for r in res:
        if len(r.keys()) == 3 and r.has_key('s') and \
            r.has_key('p') and r.has_key('o'):
            print_string += '%s\n' % r['s']
            print_string += '\t%s\n' % r['p']
            print_string += '\t\t%s\n' % r['o']
            print_string += '\n'
        else:
            for k,v in r.iteritems():
                print_string += '%s %s\n' (k, v)
            print_string += '\n'
    return print_string



### blank node queries #####

def get_property(fuseki_process, po_dict, debug=False):
    """return one property record, matching the pred_obj dictionary
    create one if it does not exist"""
    allowed_predicates = set(('mr:name','rdfs:literal',
                            'mr:length'))
    single_predicates = allowed_predicates
    preds = set(po_dict.keys())
    if not preds.issubset(allowed_predicates):
        ec = '''{} is not a subset of the allowed predicates set
                for a value record {}'''.format(preds, allowed_preds)
        raise ValueError(ec)
    subj_pref = 'http://www.metarelate.net/metOcean/property'
    count_string = ''
    search_string = ''
    filter_string = ''
    assign_string = ''
    for pred in po_dict.keys():
        if isinstance(po_dict[pred], list):
            if len(po_dict[pred]) != 1 and pred in single_predicates:
                ec = 'get_property only accepts 1 statement per predicate {}'
                ec = ec.format(str(po_dict))
                raise ValueError(ec)
            else:
                counter = 0
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
                    counter +=1
                assign_string += '''
                %s ?%s ;''' % (pred, pred.split(':')[-1])
                count_string += '''COUNT(DISTINCT(?%(p)s)) AS ?%(p)ss
                ''' % {'p':pred.split(':')[-1]}
                filter_string += '''
                FILTER(?%ss = %i)''' % (pred.split(':')[-1], counter)
        else:
            search_string += '''
            %s %s ;''' % (pred, po_dict[pred])
            assign_string += '''
            %s ?%s ;''' % (pred, pred.split(':')[-1])
            count_string += '''(COUNT(DISTINCT(?%(p)s)) AS ?%(p)ss)
            ''' % {'p':pred.split(':')[-1]}
            filter_string += '''
            FILTER(?%ss = %i)''' % (pred.split(':')[-1], 1)
    if search_string != '':
        qstr = '''SELECT ?property
        WHERE { {
        SELECT ?property        
        %(count)s
        WHERE{
        GRAPH <http://metarelate.net/concepts.ttl> {
        ?property %(assign)s %(search)s
        .
        } }
        GROUP BY ?property
        }
        %(filter)s
        }
        ''' % {'count':count_string,'assign':assign_string,
               'search':search_string, 'filter':filter_string}
        results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 0:
            sha1 = make_hash(po_dict)
            instr = '''INSERT DATA {
            GRAPH <http://metarelate.net/concepts.ttl> {
            <%s/%s> rdf:type skos:Concept ;
                    %s
            mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, sha1, search_string)
            insert_results = fuseki_process.run_query(instr, update=True,
                                                      debug=debug)
            results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 1:
            results = results[0]
        elif len(results) == 0:
            results = None
        else:
            raise ValueError('''multiple results returned from get_property,
            only one allowed
            {}'''.format(str(results)))
    else:
        results = None
    return results

def retrieve_property(fuseki_process, prop_id, debug=False):
    """
    retrieve a property record from it's id
    or None if one does not exist
    """
    qstr = '''SELECT ?property ?name ?literal ?length
    WHERE {
    GRAPH <http://metarelate.net/concepts.ttl> {
        ?property mr:name ?name ;
                  rdfs:literal ?literal ;
                  mr:length ?length .
        FILTER(?value = %s)
        }
    }
    ''' % prop_id
    results = fuseki_process.run_query(qstr, debug=debug)
    if len(results) == 0:
        prop = None
    elif len(results) >1:
        raise ValueError('{} is a malformed value'.format(results))
    else:
        prop = results[0]
    return val

    
    

def get_format_concept(fuseki_process, po_dict, debug=False):
    """return a formatConcept record ID and format, matching the
    pred_obj dictionary
    create one if it does not exist"""
    allowed_prefixes = set(('mr:format','skos:member', 'dc:requires',
                            'dc:mediates'))
    preds = set(po_dict.keys())
    if not preds.issubset(allowed_prefixes):
        ec = '''{} is not a subset of the allowed predicates set for
                a formatConcept record {}'''
        ec = ec.format(preds, allowed_prefixes)
        raise ValueError(ec)
    subj_pref = 'http://www.metarelate.net/metOcean/formatConcept'
    search_string = ''
    n_members = 0
    n_reqs = 0
    for pred in po_dict.keys():
        if isinstance(po_dict[pred], list):
            if pred == 'mr:format' and len(po_dict[pred]) != 1:
                ec = '''get_format_concept only accepts 1 mr:format statement
                        The po_dict in this case is not valid
                        {} '''
                ec = ec.format(str(po_dict))
                raise ValueError(ec)
            elif pred == 'dc:mediates' and len(po_dict[pred]) != 1:
                ec = '''get_format_concept only accepts 1 dc:mediates statement
                        The po_dict in this case is not valid
                        {} '''
                ec = ec.format(str(po_dict))
                raise ValueError(ec)
            elif pred == 'dc:requires':
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
                    n_reqs +=1
            elif pred == 'skos:member':
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
                    n_members +=1
            else:
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
        else:
            search_string += '''
            %s %s ;''' % (pred, po_dict[pred])
            if pred == 'skos:member':
                n_members =1
    if search_string != '':
        qstr = '''SELECT ?formatConcept ?format
        WHERE { {
        SELECT ?formatConcept ?format
        (COUNT(DISTINCT(?member)) AS ?members)
        (COUNT(DISTINCT(?requires)) AS ?requireses)        
        WHERE{
        GRAPH <http://metarelate.net/concepts.ttl> {
        ?formatConcept mr:format ?format ;
                       skos:member ?member ;
               %s .
        OPTIONAL{?formatConcept dc:requires ?requires .}
        OPTIONAL{?formatConcept dc:mediates ?mediates .}
        } }
        GROUP BY ?formatConcept ?format 
        }
        FILTER(?members = %i)
        FILTER(?requireses = %i)
        }
        ''' % (search_string, n_members, n_reqs)
        results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 0:
            sha1 = make_hash(po_dict)
            instr = '''INSERT DATA {
            GRAPH <http://metarelate.net/concepts.ttl> {
            <%s/%s> rdf:type skos:Concept ;
                    rdf:type skos:ConceptScheme ;
                    %s
                    mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, sha1, search_string)
            insert_results = fuseki_process.run_query(instr, update=True,
                                                      debug=debug)
            results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 1:
            results = results[0]
        else:
            raise ValueError('''multiple results returned from
            get_format_concept, only one allowed
            {}'''.format(str(results)))
    else:
        results = None
    return results

def retrieve_format_concept(fuseki_process, fcId, debug=False):
    """
    return a formatConcept record from the provided id
    or None if one does not exist
    """
    qstr = '''SELECT ?formatConcept ?format ?mediates 
    (GROUP_CONCAT(?amember; SEPARATOR='&') AS ?member)
    (GROUP_CONCAT(?arequires; SEPARATOR='&') AS ?requires)
    WHERE {
    GRAPH <http://metarelate.net/concepts.ttl> {
        ?formatConcept mr:format ?format ;
                       skos:member ?amember ;.
        OPTIONAL{?formatConcept dc:requires ?arequires .}
        OPTIONAL{?formatConcept dc:mediates ?mediates .}
        FILTER(?formatConcept = %s)
        }
    }
    GROUP BY ?formatConcept ?format ?mediates
    ''' % fcId
    results = fuseki_process.run_query(qstr, debug=debug)
    if len(results) == 0:
        fCon = None
    elif len(results) >1:
        raise ValueError('{} is a malformed formatConcept'.format(results))
    else:
        fCon = results[0]
    return fCon

def get_value_map(fuseki_process, po_dict, debug=False):
    """return a valueMap record ID, matching the pred_obj dictionary
    create one if it does not exist"""
    allowed_preds = set(('mr:source','mr:target'))
    preds = set(po_dict.keys())
    if not preds == allowed_preds:
        ec = '''{} is not a subset of the allowed predicates set
                for a valueMap record
                {}'''
        ec = ec.format(preds, allowed_preds)
        raise ValueError(ec)
    subj_pref = 'http://www.metarelate.net/metOcean/valueMap'
    search_string = ''
    for pred in po_dict.keys():
        if isinstance(po_dict[pred], list):
            if len(po_dict[pred]) != 1:
                ec = 'get_format_concept only accepts 1 mr:format statement }'
                ec = ec.format(po_dict)
                raise ValueError(ec)
            else:
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
        else:
            search_string += '''
            %s %s ;''' % (pred, po_dict[pred])
    if search_string != '':
        qstr = '''SELECT ?valueMap 
        WHERE{
        GRAPH <http://metarelate.net/concepts.ttl> {
        ?valueMap
               %s .
        }
        }
        ''' % (search_string)
        results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 0:
            sha1 = make_hash(po_dict)
            instr = '''INSERT DATA {
            GRAPH <http://metarelate.net/concepts.ttl> {
            <%s/%s> rdf:type skos:Concept ;
                    %s
                    mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, sha1, search_string)
            insert_results = fuseki_process.run_query(instr, update=True,
                                                      debug=debug)
            results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 1:
            results = results[0]
        else:
            raise ValueError('''multiple results returned from
            get_calue_map, only one allowed
            {}'''.format(str(results)))
    else:
        results = None
    return results

def get_value(fuseki_process, po_dict, debug=False):
    """return a value record ID, matching the pred_obj dictionary
    create one if it does not exist"""
    allowed_preds = set(('mr:operator','mr:subject', 'mr:object'))
    preds = set(po_dict.keys())
    if not preds.issubset(allowed_preds):
        ec = '''{} is not a subset of the allowed predicates set
                for a value record
                {}'''
        ec = ec.format(preds, allowed_preds)
        raise ValueError(ec)
    subj_pref = 'http://www.metarelate.net/metOcean/value'
    search_string = ''
    for pred in po_dict.keys():
        if isinstance(po_dict[pred], list):
            if len(po_dict[pred]) != 1:
                ec = 'get_value only accepts 1 mr:format statement }'
                ec = ec.format(po_dict)
                raise ValueError(ec)
            else:
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
        else:
            search_string += '''
            %s %s ;''' % (pred, po_dict[pred])
    if search_string != '':
        qstr = '''SELECT ?value
        WHERE{
        GRAPH <http://metarelate.net/concepts.ttl> {
        ?value
               %s .
        }
        }
        ''' % (search_string)
        results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 0:
            sha1 = make_hash(po_dict)
            instr = '''INSERT DATA {
            GRAPH <http://metarelate.net/concepts.ttl> {
            <%s/%s> rdf:type skos:Concept ;
                    %s
                    mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, sha1, search_string)
            insert_results = fuseki_process.run_query(instr, update=True,
                                                      debug=debug)
            results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 1:
            results = results[0]
        else:
            raise ValueError('''multiple results returned from
            get_value, only one allowed
            {}'''.format(str(results)))
    else:
        results = None
    return results

def get_scoped_property(fuseki_process, po_dict, debug=False):
    """return a scopedProperty record ID, matching the pred_obj dictionary
    create one if it does not exist"""
    allowed_preds = set(('mr:scope','mr:property'))
    preds = set(po_dict.keys())
    if not preds == allowed_preds:
        ec = '''{} is not a subset of the allowed predicates set
                for a scopedProperty record
                {}'''
        ec = ec.format(preds, allowed_preds)
        raise ValueError(ec)
    subj_pref = 'http://www.metarelate.net/metOcean/scopedProperty'
    search_string = ''
    for pred in po_dict.keys():
        if isinstance(po_dict[pred], list):
            if len(po_dict[pred]) != 1:
                ec = 'get_scopedProperty only accepts 1 mr:format statement }'
                ec = ec.format(po_dict)
                raise ValueError(ec)
            else:
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
        else:
            search_string += '''
            %s %s ;''' % (pred, po_dict[pred])
    if search_string != '':
        qstr = '''SELECT ?scopedProperty
        WHERE{
        GRAPH <http://metarelate.net/concepts.ttl> {
        ?scopedProperty
               %s .
        }
        }
        ''' % (search_string)
        results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 0:
            sha1 = make_hash(po_dict)
            instr = '''INSERT DATA {
            GRAPH <http://metarelate.net/concepts.ttl> {
            <%s/%s> rdf:type skos:Concept ;
                    %s
                    mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, sha1, search_string)
            insert_results = fuseki_process.run_query(instr, update=True,
                                                      debug=debug)
            results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 1:
            results = results[0]
        else:
            raise ValueError('''multiple results returned from
            get_scopedProperty, only one allowed
            {}'''.format(str(results)))
    else:
        results = None
    return results


# def retrieve_valuemap(fuseki_process, vmId, debug=False):
#     """
#     return a valueMap record from the provided id
#     or None if one does not exist
#     """
#     qstr = '''SELECT ?valueMap ?source ?target
#     ?sourceScope
#     ?sourceValue ?sourceProperty
#     ?targetScope
#     ?targetValue ?targetProperty
#     WHERE {
#     GRAPH <http://metarelate.net/concepts.ttl> {
#         ?valueMap mr:source ?source ;
#                   mr:target ?target .
#         ?source mr:scope ?asourceScope ;
#                 mr:value ?sourceValue .
#         OPTIONAL{?sourceValue rdf:Property ?sourceProperty .}
#         ?target mr:scope ?atargetScope ;
#                 mr:value ?targetValue .
#         OPTIONAL{?targetValue rdf:Property ?targetProperty .}
#         FILTER(?valueMap = %s)
#         }
#     }
#     GROUP BY ?valueMap ?source ?target
#     ?sourceValue ?sourceProperty
#     ?targetValue ?targetProperty
#     ''' % vmId
#     results = fuseki_process.run_query(qstr, debug=debug)
#     if len(results) == 0:
#         valuemap = None
#     elif len(results) >1:
#         raise ValueError('{} is a malformed valueMap'.format(results))
#     else:
#         valuemap = results[0]
#     return valuemap



def get_contact(fuseki_process, subject, po_dict, debug=False):
    """return a contact record ID, matching the pred_obj dictionary
    create one if it does not exist"""
    allowed_prefixes = set(('skos:inScheme', 'dc:dateAccepted'))
    preds = set(po_dict.keys())
    if not preds.issubset(allowed_prefixes):
        ec = '''{}
            is not a subset of the allowed predicates set for a contact record
            {}'''
        ec = ec.format(preds, allowed_preds)
        raise ValueError(ec)
    search_string = ''
    for pred in po_dict.keys():
        if isinstance(po_dict[pred], list):
            if len(po_dict[pred]) == 1:
                ec = 'get_format_concept accepts 1 statement per predicate {}'
                ec = ec.format(str(po_dict))
                raise ValueError(ec)
            else:
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
        else:
            search_string += '''
            %s %s ;''' % (pred, po_dict[pred])
    if search_string != '':
        qstr = '''SELECT DISTINCT ?contact 
        WHERE{
        GRAPH <http://metarelate.net/contacts.ttl> {
        ?contact ?p ?o .
        filter (?contact = <%s>)
        }
        }
        ''' % (subject)
        results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 0:
            instr = '''INSERT DATA {
            GRAPH <http://metarelate.net/contacts.ttl> {
            <%s> rdf:type skos:Concept ;
                    %s
                    mr:saveCache "True" .
            }
            }
            ''' % (subject, search_string)
            insert_results = fuseki_process.run_query(instr, update=True,
                                                      debug=debug)
            results = fuseki_process.run_query(qstr, debug=debug)
        if len(results) == 1:
            results = results[0]
        else:
            raise ValueError('''multiple results returned from
            get_contact, only one allowed
            {}'''.format(str(results)))
    else:
        results = None
    return results



def create_mapping(fuseki_process, po_dict, debug=False):
    """create a new mapping record using the po_dict
    """
    subj_pref = 'http://metarelate.net/metocean/mapping'
    allowed_prefixes = set(('mr:source', 'mr:target', 'mr:invertible',
                            'dc:replaces', 'mr:valueMap', 'mr:status',
                            'skos:note', 'mr:reason', 'dc:date', 'dc:creator',
                            'mr:owner', 'mr:watcher'))
    preds = set(po_dict.keys())
    if not preds.issubset(allowed_prefixes):
        ec = '''{}
        is not a subset of the allowed predicates set for a mapping record
        {}'''
        ec = ec.format(preds, allowed_preds)
        raise ValueError(ec)
    mandated_prefixes = set(('mr:source', 'mr:target', 'mr:invertible', 
                            'mr:status',  'mr:reason',
                            'dc:date', 'dc:creator'))
    if not preds.issuperset(mandated_prefixes):
        ec = '''{}
        is not a superset of the mandated predicates set for a mapping record
        {}'''
        ec = ec.format(preds, mandated_prefixes)
        raise ValueError(ec)
    singular_prefixes = set(('mr:source', 'mr:target', 'mr:invertible',
                             'dc:replaces', 'mr:status', 'skos:note',
                             'mr:reason', 'dc:date', 'dc:creator'))
    search_string = ''
    for pred in po_dict.keys():
        if isinstance(po_dict[pred], list):
            if pred in singular_prefixes and len(po_dict[pred]) != 1:
                ec = 'create_mapping limits {} to one statement per record '
                ec = ec.format(pred)
                raise ValueError(ec)
            else:
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
        else:
            search_string += '''
            %s %s ;''' % (pred, po_dict[pred])
    sha1 = make_hash(po_dict, ['''dc:date'''])
    mapping = '%s/%s' % (subj_pref, sha1)
    qstr = '''SELECT ?mapping
    WHERE {
    GRAPH <http://metarelate.net/mappings.ttl> {
    ?mapping rdf:type skos:Concept .
    FILTER(?mapping = <%s>)
    } }''' % mapping
    results = fuseki_process.run_query(qstr, debug=debug)
    if results == []:
        #create the mapping
        instr = '''INSERT DATA {
        GRAPH <http://metarelate.net/mappings.ttl> {
        <%s> rdf:type skos:Concept ;
                    %s
                    mr:saveCache "True" .
        }
        }
        ''' % (mapping, search_string)
        insert_results = fuseki_process.run_query(instr, update=True,
                                                  debug=debug)
    return [{'map':'<{}>'.format(mapping)}]


def get_mapping_by_id(fuseki_process, map_id, debug=False):
    """
    return a mapping record if one exists, from the provided id
    """
    qstr = '''SELECT ?mapping ?source ?target ?invertible ?replaces ?status
                     ?note ?reason ?date ?creator
    (GROUP_CONCAT(DISTINCT(?owner); SEPARATOR = '&') AS ?owners)
    (GROUP_CONCAT(DISTINCT(?watcher); SEPARATOR = '&') AS ?watchers)
    (GROUP_CONCAT(DISTINCT(?valueMap); SEPARATOR = '&') AS ?valueMaps)
    WHERE {
    GRAPH <http://metarelate.net/mappings.ttl> {
    ?mapping mr:source ?source ;
         mr:target ?target ;
         mr:invertible ?invertible ;
         mr:status ?status ;
         mr:reason ?reason ;
         dc:date ?date ;
         dc:creator ?creator .
    OPTIONAL {?mapping dc:replaces ?replaces .}
    OPTIONAL {?mapping skos:note ?note .}
    OPTIONAL {?mapping mr:valueMap ?valueMap .}
    OPTIONAL {?mapping mr:owner ?owner .}
    OPTIONAL {?mapping mr:watcher ?watcher .}
    FILTER(?mapping = %s)
    }
    }
    GROUP BY ?mapping ?source ?target ?invertible ?replaces
             ?status ?note ?reason ?date ?creator
    ''' % str(map_id)
    result = fuseki_process.run_query(qstr, debug=debug)
    if result == []:
        result = None
    elif len(result) == 1:
        result = result[0]
    else:
        raise ValueError('''%s is not a valid mapping, it has multiple returns:
        %s ''' % (map_id, result))
    return result





###validation rules

def multiple_mappings(fuseki_process, debug=False):
    """
    returns all the mappings which map the same source to a different target
    """
    qstr = '''SELECT ?amap ?asource ?atarget ?bmap ?bsource ?btarget
    WHERE {
    GRAPH <http://metarelate.net/mappings.ttl> { {
    ?amap mr:status ?astatus ;
         mr:source ?asource ;
         mr:target ?atarget . } 
    UNION 
        { 
    ?amap mr:invertible "True" ;
         mr:status ?astatus ;
         mr:target ?asource ;
         mr:source ?atarget . } 
    FILTER (?astatus NOT IN ("Deprecated", "Broken"))
    MINUS {?amap ^dc:replaces+ ?anothermap}
    } 
    GRAPH <http://metarelate.net/mappings.ttl> { {
    ?bmap mr:status ?bstatus ;
         mr:source ?bsource ;
         mr:target ?btarget . } 
    UNION  
        { 
    ?bmap mr:invertible "True" ;
         mr:status ?bstatus ;
         mr:target ?bsource ;
         mr:source ?btarget . } 
    FILTER (?bstatus NOT IN ("Deprecated", "Broken"))
    MINUS {?bmap ^dc:replaces+ ?bnothermap}
    filter (?bmap != ?amap)
    filter (?bsource = ?asource)
    filter (?btarget != ?atarget)
    } 
    GRAPH <http://metarelate.net/concepts.ttl> {
    ?asource mr:format ?asourceformat .
    ?bsource mr:format ?bsourceformat .
    ?atarget mr:format ?atargetformat .
    ?btarget mr:format ?btargetformat .
    }
    filter (?btargetformat = ?atargetformat)
    }
    ORDER BY ?asource
    '''
    results = fuseki_process.run_query(qstr, debug=debug)
    return results











 










##### legacy ###
######  not functional, not for review #######
######  to end ###########
def current_mappings(fuseki_process, debug=False):
    """
    return all triples currently valid in the mappings graph
    """
    qstr = '''
    SELECT ?s ?p ?o
    WHERE
    { GRAPH <http://metarelate.net/mappings.ttl> {
    ?s ?p ?o ;
        mr:status ?status.
        FILTER (?status NOT IN ("Deprecated", "Broken")) .
        {
          SELECT ?map ?replaces
          WHERE
          {
           ?map dc:replaces ?replaces .

           MINUS {?map ^dc:replaces+ ?map}
           }
        }
    }
    '''
    results = fuseki_process.run_query(qstr, update=True, debug=debug)
    return results



def select_graph(fuseki_process, graph, debug=False):
    """
    selects a particular graph from the TDB
    """
    qstr = '''
        SELECT DISTINCT ?g
        WHERE {
            GRAPH ?g { ?s ?p ?o } .
            FILTER( REGEX(str(?g), '%s') ) .
        }

    ''' % graph
    results = fuseki_process.run_query(qstr, debug=debug)
    return results




def subject_by_graph(fuseki_process, graph, debug=False):
    """
    selects distinct subject from a particular graph
    """
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
    """
    selects distinct subject from a particular graph matching a pattern
    """
    qstr = '''
        SELECT DISTINCT ?subject
        WHERE {
            GRAPH <http://%s> { ?subject ?p ?o } .
            FILTER( REGEX(str(?subject), '%s') ) .            
        }
        ORDER BY ?subject

    ''' % (graph,pattern)

    results = fuseki_process.run_query(qstr, debug=debug)
    return results



# def concept_components(fuseki_process, concepts, debug=False):
#     """
#     return all the components for a particular list of concept
#     """
#     comma = ', '
#     cons = ['<%s>' % result['concept'] for result in concepts]
#     con_str = comma.join(cons)

#     qstr = '''SELECT ?concept
#     (GROUP_CONCAT(DISTINCT(?component); SEPARATOR = "&") AS ?components)
#     (GROUP_CONCAT(DISTINCT(?cfitem); SEPARATOR = "&") AS ?cfitems)
#     WHERE
#     { GRAPH <http://metarelate.net/concepts.ttl> {
#         ?concept mr:component ?component .
#         filter ( ?concept in (%s))
#         }
#      OPTIONAL { GRAPH <http://metarelate.net/cflinks.ttl> {
#      ?component ?cfp ?cfo .
#      BIND(CONCAT(STR(?cfp), ";", STR(?cfo)) AS ?cfitem) } }        
#         }
#         GROUP BY ?concept
#         ORDER BY ?component
#     ''' % con_str
#     results = fuseki_process.run_query(qstr, debug=debug)
#     return results

# def get_superset_concept(fuseki_process, po_dict, debug=False):
#     """
#     return the concepts which are a superset of the elements in the
#     predicate object dictionary
#     """
#     subj_pref = 'http://www.metarelate.net/metOcean/concept'
#     search_string = ''
#     if po_dict:
#         for pred in po_dict.keys():
#             if isinstance(po_dict[pred], list):
#                 for obj in po_dict[pred]:
#                     search_string += '''
#                     %s %s ;''' % (pred, obj)
#             else:
#                 search_string += '''
#                 %s %s ;''' % (pred, po_dict[pred])
#     if search_string != '':
#         search_string += '.'
        
#         qstr = '''SELECT ?concept 
#         WHERE
#         { GRAPH <http://metarelate.net/concepts.ttl> {
#         ?concept %s
#         }
#         }
#         ''' % (search_string)
#         results = fuseki_process.run_query(qstr, debug=debug)
#     else:
#         results = []
#     return results

# def get_concepts_by_format(fuseki_process, fformat, prefix=None, n_components=None, debug=False):
#     """
#     returns the concepts matching the format with components matching the prefixes
#     optionally allows a limit to number of components
#     Args:
#     * format:
#     the format of the concept
#     * prefix:
#     the prefix strings to match to components
#     * n_components:
#     the number of components the concept must have
#     """
#     nfilter = ''
#     if n_components:
#         nfilter = 'filter (?ncomponents = %i)' % n_components
#     prefilter = ''
#     if prefix:
#         prefilter = 'filter (regex(str(?comp), "%s"))' % prefix
#     qstr = '''
#     SELECT ?concept
#     WHERE
#     {
#         {SELECT ?concept (COUNT(?concept) as ?ncomponents)
#         WHERE
#         { GRAPH <http://metarelate.net/concepts.ttl> {
#         ?concept mr:format <%(fformat)s> .
#         }
#         }
#         GROUP BY ?concept
#         }
#         {SELECT ?fconcept
#         WHERE
#         { GRAPH <http://metarelate.net/concepts.ttl> {
#         ?fconcept mr:format <%(fformat)s> ;
#                  mr:component ?comp .
#         %(prefilter)s 
#         }
#         }
#     }
#     filter (?fconcept = ?concept)
#     %(ncomp)s
#     }
#     ''' % {'fformat':fformat, 'prefilter':prefilter, 'ncomp':nfilter}
#     results = fuseki_process.run_query(qstr, debug=debug)
#     return results


# def get_concept(fuseki_process, po_dict, debug=False, create=True):
#     """
#     return the concept which matches the predicate object
#     dictionary exactly
#     create it if it does not exist
#     """
#     subj_pref = 'http://www.metarelate.net/metOcean/concept'
#     search_string = ''
#     n_components = 0
#     for pred in po_dict.keys():
#         if isinstance(po_dict[pred], list):
#             if pred == 'mr:component':
#                 n_components = len(po_dict[pred])
#             for obj in po_dict[pred]:
#                 search_string += '''
#                 %s %s ;''' % (pred, obj)
#         else:
#             if pred == 'mr:component':
#                 n_components = 1
#             search_string += '''
#             %s %s ;''' % (pred, po_dict[pred])
#     if search_string != '':
#         search_string += '.'
        
#         qstr = '''SELECT ?concept
#         WHERE{
#         filter (?componentcount = %i)
#         {SELECT ?concept (COUNT(?component) as ?componentcount)
#         WHERE
#         { GRAPH <http://metarelate.net/concepts.ttl> {
#         ?concept mr:component ?component ;
#                 %s
#         }
#         }
#         GROUP BY ?concept
#         }
#         }
#         ''' % (n_components, search_string)
#         results = fuseki_process.run_query(qstr, debug=debug)
#         #if len(results) == 1 and results[0] == {}:
#         if len(results) == 0 and create:
#             md5 = make_hash(po_dict)
#             instr = '''INSERT DATA
#             { GRAPH <http://metarelate.net/concepts.ttl> {
#             <%s/%s> %s
#             mr:saveCache "True" .
#             }
#             }
#             ''' % (subj_pref, md5, search_string.rstrip('.'))
#             insert_results = fuseki_process.run_query(instr, update=True, debug=debug)
#             results = fuseki_process.run_query(qstr, debug=debug)
#     else:
#         results = []
#     return results

def mappings_by_ordered_concept(fuseki_process, source_list, target_list, debug=False):
    """
    return mapping records matching elements in the concepts list as sources or targets
    """
    sources = ','.join(source_list)
    targets = ','.join(target_list)
    qstr = ''' SELECT ?map ?source ?target
    WHERE
    {GRAPH <http://metarelate.net/mappings.ttl> {
    {?map mr:source ?source ;
         mr:target ?target .
       filter(?source in (%s))
       filter(?target in (%s))}
        }
    }
    ''' % (sources, targets)
    results = fuseki_process.run_query(qstr, debug=debug)
    return results


def mappings_by_concept(fuseki_process, concepts, debug=False):
    """
    return mapping records matching elements in the concepts list as sources or targets
    """
    sources = ','.join(concepts)
    targets = ','.join(concepts)
    qstr = ''' SELECT ?map ?source ?target
    WHERE
    {GRAPH <http://metarelate.net/mappings.ttl> {
    {?map mr:source ?source ;
         mr:target ?target .
       filter(?source in (%s))}
         UNION
         {?map mr:source ?source ;
         mr:target ?target .
       filter(?target in (%s))}
        }
    }
    ''' % (sources, targets)
    results = fuseki_process.run_query(qstr, debug=debug)
    return results


