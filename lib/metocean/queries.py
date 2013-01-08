

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
    """ creates and returns an md5 hash of the elements in the pred_obj
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
    mmd5 = hashlib.md5()
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
                    mmd5.update(predicate)
                    mmd5.update(obj)
            else:
                mmd5.update(predicate)
                mmd5.update(pred_obj[pred])
    md5 = str(mmd5.hexdigest())
    return md5
    

def revert_cache(fuseki_process, graph, debug=False):
    """
    update a graph in the triple database removing all records flagged with the saveCache predicate
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

# def mapping_by_link(fuseki_process, paramlist=False,debug=False):
#     """
#     return all the valid mappings, with linkage and cf elements for a given data format and linklist, 
#     or all mappings if linklist is left as False 
#     """
#     linkpattern = ''
#     if paramlist:
#         linkpattern = '''          ?link '''
#         for param in paramlist:
#             linkpattern += '''
#                     mr:%slink <%s> ;
#             ''' % (param[0].upper(),param[1])
#         linkpattern.rstrip(';')
#         linkpattern += ' .'
#     qstr = '''
#     SELECT ?map
#        (GROUP_CONCAT(DISTINCT(?owner); SEPARATOR = ",") AS ?owners)
#        (GROUP_CONCAT(DISTINCT(?watcher); SEPARATOR = ",") AS ?watchers) 
#        ?creator 
#        ?creation 
#        ?status 
#        ?replaces
#        ?comment
#        ?reason
#        ?link
#        (GROUP_CONCAT(DISTINCT(?cfitem); SEPARATOR = "&") AS ?cfelems) 
#        (GROUP_CONCAT(DISTINCT(?cflink); SEPARATOR = "&") AS ?cflinks)
#        ?cfim ?cfex 
#        (GROUP_CONCAT(DISTINCT(?umlink); SEPARATOR = "&") AS ?umlinks)
#        ?umim ?umex 
#        (GROUP_CONCAT(DISTINCT(?griblink); SEPARATOR = "&") AS ?griblinks)
#        ?gribim ?gribex
#        WHERE
#        {
#               GRAPH <http://metocean/cflinks.ttl> {
#               ?cflink ?cfp ?cfo .
#               BIND(CONCAT(STR(?cfp), ";", STR(?cfo)) AS ?cfitem)
#               }
#        { SELECT ?map ?owner ?watcher ?creator ?creation ?status ?replaces ?comment ?reason ?link ?cflink ?umlink ?griblink

#        WHERE { GRAPH <http://metocean/mappings.ttl> {
#            ?map mr:owner ?owner ;
#                 mr:watcher ?watcher ;
#                 mr:creator ?creator ;
#                 mr:creation ?creation ;
#                 mr:status ?status ;
#                 dc:replaces ?replaces ;
#                 mr:comment ?comment ;
#                 mr:reason ?reason ;
#                 mr:linkage ?link .

#        FILTER (?status NOT IN ("Deprecated", "Broken"))
#        MINUS {?map ^dc:replaces+ ?map}
#        } GRAPH <http://metocean/linkages.ttl> {
# %s
#        OPTIONAL
#            {?link mr:CFlink ?cflink ;
#                   mr:CFimport ?cfim ;
#                   mr:CFexport ?cfex . }
#        OPTIONAL
#            {?link mr:UMlink ?umlink ;
#                   mr:UMimport ?umim ;
#                   mr:UMexport ?umex . }
#        OPTIONAL
#            {?link mr:GRIBlink ?griblink ;
#                   mr:GRIBimport ?gribim ;
#                   mr:GRIBexport ?gribex .}
              

#     } } } }
#     GROUP BY ?map ?creator ?creation ?status ?replaces ?comment ?reason ?link ?cfim ?cfex ?umim ?umex ?gribim ?gribex
#     ''' % (linkpattern)
#     results = fuseki_process.run_query(qstr, debug=debug)
#     return results

# def fast_mapping_by_link(fuseki_process, dataformat,linklist=False,debug=False):
#     """
#     return all the valid mappings, with linkage and cf elements for a given data format and linklist, 
#     or all mappings if linklist is left as False 
#     """
#     linkpattern = ''
#     if linklist:
#         linkpattern = '''          ?link '''
#         for link in linklist:
#             linkpattern += '''
#                     mr:%slink <%s> ;
#             ''' % (dataformat.upper(),link)
#         linkpattern.rstrip(';')
#         linkpattern += ' .'
#     qstr = '''
#     SELECT ?map
#        (GROUP_CONCAT(DISTINCT(?owner); SEPARATOR = ",") AS ?owners)
#        (GROUP_CONCAT(DISTINCT(?watcher); SEPARATOR = ",") AS ?watchers) 
#        ?creator 
#        ?creation 
#        ?status 
#        ?replaces
#        ?comment
#        ?reason
#        ?link
#        (GROUP_CONCAT(DISTINCT(?cflink); SEPARATOR = "&") AS ?cflinks)
#        ?cfim ?cfex 
#        (GROUP_CONCAT(DISTINCT(?umlink); SEPARATOR = "&") AS ?umlinks)
#        ?umim ?umex
#        (GROUP_CONCAT(DISTINCT(?griblink); SEPARATOR = "&") AS ?griblinks)
#        ?gribim ?gribex

#     WHERE
      
#  { GRAPH <http://metocean/mappings.ttl> {
#            ?map mr:owner ?owner ;
#                 mr:watcher ?watcher ;
#                 mr:creator ?creator ;
#                 mr:creation ?creation ;
#                 mr:status ?status ;
#                 dc:replaces ?replaces ;
#                 mr:comment ?comment ;
#                 mr:reason ?reason ;
#                 mr:linkage ?link .
# %s
#        FILTER (?status NOT IN ("Deprecated", "Broken"))
#        MINUS {?map ^dc:replaces+ ?map}
#            }
# GRAPH <http://metocean/linkages.ttl> {
#        OPTIONAL
#            {?link mr:CFlink ?cflink ;
#                   mr:CFimport ?cfim ;
#                   mr:CFexport ?cfex . }
#        OPTIONAL
#            {?link mr:UMlink ?umlink ;
#                   mr:UMimport ?umim ;
#                   mr:UMexport ?umex . }
#        OPTIONAL
#            {?link mr:GRIBlink ?griblink ;
#                   mr:GRIBimport ?gribim ;
#                   mr:GRIBexport ?gribex .}
       

#     }}
#     GROUP BY ?map ?creator ?creation ?status ?replaces ?comment ?reason ?link ?cfim ?cfex ?umim ?umex ?gribim ?gribex
#     ''' % (linkpattern)
#     results = fuseki_process.run_query(qstr, debug=debug)
#     return results




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


# def counts_by_graph(fuseki_process, graph, debug=False):
#     """This query relies on a feature of Jena that is not yet in the official
#     SPARQL v1.1 standard insofar as 'GRAPH ?g' has undetermined behaviour
#     under the standard but Jena interprets and treats the '?g' 
#     just like any other variable.
#     """
#     qstr = '''
#         SELECT ?g (COUNT(DISTINCT ?s) as ?count)
#         WHERE {
#             GRAPH ?g { ?s ?p ?o } .
#             FILTER( REGEX(str(?g), '%s') ) .
#         }
#         GROUP by ?g
#         ORDER by ?g
#     ''' % graph
#     results = fuseki_process.run_query(qstr)
#     return results

# def count_by_graph(fuseki_process, debug=False):
#     '''This query relies on a feature of Jena that is not yet in the official
#     SPARQL v1.1 standard insofar as 'GRAPH ?g' has undetermined behaviour
#     under the standard but Jena interprets and treats the '?g' 
#     just like any other variable.
#     '''
#     qstr = '''
#         SELECT ?g (COUNT(DISTINCT ?s) as ?count)
#         WHERE {
#             GRAPH ?g { ?s ?p ?o } .
#         }
#         GROUP by ?g
#         ORDER by ?g
#     '''
#     results = fuseki_process.run_query(qstr)
#     return results



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


def get_cflink_by_id(fuseki_process, cflink, debug=False):
    """
    return a cflink record, if one exists, using the MD5 ID
    """
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
    """
    return cflink records matching the predicate object dictionary items
    """
    filterstr = ''
    if pred_obj:
        for key in pred_obj.keys():
            filterstr += '''FILTER (bound(?{key}))
            FILTER (STRSTARTS(str(?{key}), str({val})))
            FILTER (STRENDS(str(?{key}), str({val})))
            FILTER (STRLEN(str(?{key})) = STRLEN(str({val})))
            '''.format(key=key.split(':')[1], val=pred_obj[key])
    qstr  = '''
    SELECT ?s ?type ?standard_name ?units ?long_name
    WHERE
    { GRAPH <http://metarelate.net/cflinks.ttl> {
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
    """
    create a new link, using the provided predicates:objectsList dictionary, if one does not already exists.
    if one already exists, use this in preference
    subj_pref is the prefix for the subject, e.g. http://www.metarelate.net/metocean/cf, http://www.metarelate.net/metocean/linkage
    """
    md5 = make_hash(po_dict)

    current_link = get_cflinks(fuseki_process, po_dict)
    if len(current_link) == 0:
        pred_obj = ''
        for pred in po_dict.keys():
            pattern_string = ''' %s %s ;
            ''' % (pred, po_dict[pred])
            pred_obj += pattern_string
        qstr = '''
        INSERT DATA
        { GRAPH <http://metarelate.net/cflinks.ttl>
        { <%s/%s> %s
        mr:saveCache "True" .
        }
        }
        ''' % (subj_pref, md5, pred_obj)
        results = fuseki_process.run_query(qstr, update=True, debug=debug)
        current_link = get_cflinks(fuseki_process, po_dict)
    return current_link


# def get_linkage(fuseki_process, fso_dict, debug=False):
#     """
#     return a linkage if one exists, using the full record:
#         a dictionary of format strings and lists of objects.
#     if one does not exist, create it
#     """
#     subj_pref = 'http://www.metarelate.net/metOcean/linkage'
#     search_string = ''
#     for fstring in fso_dict.keys():
#         if isinstance(fso_dict[fstring], list):
#             for obj in fso_dict[fstring]:
#                 search_string += '''
#                 %s %s ;''' % (fstring, obj)
#         else:
#             search_string += '''
#             %s %s ;''' % (fstring, fso_dict[fstring])
#     if search_string != '':
#         search_string += '.'
#         qstr = '''
#         SELECT ?linkage
#             (GROUP_CONCAT(DISTINCT(?cflink); SEPARATOR = "&") AS ?cflinks) 
#             (GROUP_CONCAT(DISTINCT(?umlink); SEPARATOR = "&") AS ?umlinks)
#             (GROUP_CONCAT(DISTINCT(?griblink); SEPARATOR = "&") AS ?griblinks)

#         WHERE
#         { GRAPH <http://metocean/linkages.ttl>{
#             ?linkage %s
#        OPTIONAL
#            {?linkage mr:CFlink ?cflink . }
#        OPTIONAL
#            {?linkage mr:UMlink ?umlink . }
#        OPTIONAL
#            {?linkage mr:GRIBlink ?griblink .}
#             FILTER (regex(str(?linkage),"%s", "i"))
#             }
#         }
#         GROUP BY ?linkage
#         ''' % (search_string, subj_pref)

#         results = fuseki_process.run_query(qstr, debug=debug)
#         if len(results) == 1 and results[0] == {}:
#             pre = prefixes.Prefixes()
#             md5 = make_hash(fso_dict)

#             inststr = '''
#             INSERT DATA
#             { GRAPH <http://metocean/linkages.ttl>
#             { <%s/%s> %s
#             mr:saveCache "True" .
#             }
#             }
#             ''' % (subj_pref, md5, search_string.rstrip('.'))
#             insert_results = fuseki_process.run_query(inststr, update=True, debug=debug)
 #             results = fuseki_process.run_query(qstr, debug=debug)
#     else:
#         results = []

#     return results

def concept_components(fuseki_process, concepts, debug=False):
    """
    return all the components for a particular list of concept
    """
    comma = ', '
    cons = ['<%s>' % result['concept'] for result in concepts]
    con_str = comma.join(cons)

    qstr = '''SELECT ?concept
    (GROUP_CONCAT(DISTINCT(?component); SEPARATOR = "&") AS ?components)
    (GROUP_CONCAT(DISTINCT(?cfitem); SEPARATOR = "&") AS ?cfitems)
    WHERE
    { GRAPH <http://metarelate.net/concepts.ttl> {
        ?concept mr:component ?component .
        filter ( ?concept in (%s))
        }
     OPTIONAL { GRAPH <http://metarelate.net/cflinks.ttl> {
     ?component ?cfp ?cfo .
     BIND(CONCAT(STR(?cfp), ";", STR(?cfo)) AS ?cfitem) } }        
        }
        GROUP BY ?concept
        ORDER BY ?component
    ''' % con_str
    results = fuseki_process.run_query(qstr, debug=debug)
    return results

def get_superset_concept(fuseki_process, po_dict, debug=False):
    """
    return the concepts which are a superset of the elements in the
    predicate object dictionary
    """
    subj_pref = 'http://www.metarelate.net/metOcean/concept'
    search_string = ''
    if po_dict:
        for pred in po_dict.keys():
            if isinstance(po_dict[pred], list):
                for obj in po_dict[pred]:
                    search_string += '''
                    %s %s ;''' % (pred, obj)
            else:
                search_string += '''
                %s %s ;''' % (pred, po_dict[pred])
    if search_string != '':
        search_string += '.'
        
        qstr = '''SELECT ?concept 
        WHERE
        { GRAPH <http://metarelate.net/concepts.ttl> {
        ?concept %s
        }
        }
        ''' % (search_string)
        results = fuseki_process.run_query(qstr, debug=debug)
    else:
        results = []
    return results

def get_concepts_by_format(fuseki_process, fformat, prefix=None, n_components=None, debug=False):
    """
    returns the concepts matching the format with components matching the prefixes
    optionally allows a limit to number of components
    Args:
    * format:
    the format of the concept
    * prefix:
    the prefix strings to match to components
    * n_components:
    the number of components the concept must have
    """
    nfilter = ''
    if n_components:
        nfilter = 'filter (?ncomponents = %i)' % n_components
    prefilter = ''
    if prefix:
        prefilter = 'filter (regex(str(?comp), "%s"))' % prefix
    qstr = '''
    SELECT ?concept
    WHERE
    {
        {SELECT ?concept (COUNT(?concept) as ?ncomponents)
        WHERE
        { GRAPH <http://metarelate.net/concepts.ttl> {
        ?concept mr:format <%(fformat)s> .
        }
        }
        GROUP BY ?concept
        }
        {SELECT ?fconcept
        WHERE
        { GRAPH <http://metarelate.net/concepts.ttl> {
        ?fconcept mr:format <%(fformat)s> ;
                 mr:component ?comp .
        %(prefilter)s 
        }
        }
    }
    filter (?fconcept = ?concept)
    %(ncomp)s
    }
    ''' % {'fformat':fformat, 'prefilter':prefilter, 'ncomp':nfilter}
    results = fuseki_process.run_query(qstr, debug=debug)
    return results


def get_concept(fuseki_process, po_dict, debug=False, create=True):
    """
    return the concept which matches the predicate object
    dictionary exactly
    create it if it does not exist
    """
    subj_pref = 'http://www.metarelate.net/metOcean/concept'
    search_string = ''
    n_components = 0
    for pred in po_dict.keys():
        if isinstance(po_dict[pred], list):
            if pred == 'mr:component':
                n_components = len(po_dict[pred])
            for obj in po_dict[pred]:
                search_string += '''
                %s %s ;''' % (pred, obj)
        else:
            if pred == 'mr:component':
                n_components = 1
            search_string += '''
            %s %s ;''' % (pred, po_dict[pred])
    if search_string != '':
        search_string += '.'
        
        qstr = '''SELECT ?concept
        WHERE{
        filter (?componentcount = %i)
        {SELECT ?concept (COUNT(?component) as ?componentcount)
        WHERE
        { GRAPH <http://metarelate.net/concepts.ttl> {
        ?concept mr:component ?component ;
                %s
        }
        }
        GROUP BY ?concept
        }
        }
        ''' % (n_components, search_string)
        results = fuseki_process.run_query(qstr, debug=debug)
        #if len(results) == 1 and results[0] == {}:
        if len(results) == 0 and create:
            md5 = make_hash(po_dict)
            instr = '''INSERT DATA
            { GRAPH <http://metarelate.net/concepts.ttl> {
            <%s/%s> %s
            mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, md5, search_string.rstrip('.'))
            insert_results = fuseki_process.run_query(instr, update=True, debug=debug)
            results = fuseki_process.run_query(qstr, debug=debug)
    else:
        results = []
    return results

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

def create_mapping(fuseki_process, po_dict, debug=False):
    """
    create a new mapping record from a dictionary of predicates and lists of objects
    """
    subj_pref = 'http://www.metarelate.net/metocean/mapping'
    results = None
    pre = prefixes.Prefixes()

    md5 = make_hash(po_dict, ['mr:creation'])

    pred_obj = ''
    for pred,objects in po_dict.iteritems():
        if isinstance(objects, list):
            for obj in objects:
                pattern_string = ''' %s %s ;
                ''' % (pred, obj)
                pred_obj += pattern_string
        else:
            pattern_string = ''' %s %s ;
            ''' % (pred, objects)
            pred_obj += pattern_string
    # check if we already have one:
    result = subject_graph_pattern(fuseki_process, 'http://metarelate.net/mappings.ttl',
            'http://www.metarelate.net/metocean/mapping/%s' % md5)
    if len(result) == 0:
        qstr = '''
        INSERT DATA
        { GRAPH <http://metarelate.net/mappings.ttl>
        { <%s/%s> %s
        mr:saveCache "True" .
        }
        }
        ''' % (subj_pref, md5, pred_obj)
        results = fuseki_process.run_query(qstr, update=True, debug=debug)
    return subj_pref + '/' + md5

def mapping_by_id(fuseki_process, mappings=None, debug=False):
    """
    returns a list of fully expanded mappings for a provided list of mapping IDs
    """
    search_string = ''
    if mappings:
        map_string = ', '.join(['<%s>' % mapping for mapping in mappings])
        search_string = '\tfilter (?map in (%s))' % map_string
    qstr = '''SELECT ?map
       (GROUP_CONCAT(DISTINCT(?owner); SEPARATOR = ",") AS ?owners)
       (GROUP_CONCAT(DISTINCT(?watcher); SEPARATOR = ",") AS ?watchers)
       ?creator 
       ?creation 
       ?status 
       ?replaces
       ?comment
       ?reason
       ?source
       ?source_format
       (GROUP_CONCAT(DISTINCT(?source_comp); SEPARATOR = "&") AS ?source_comps)
       (GROUP_CONCAT(DISTINCT(?sourcecfitems); SEPARATOR = "&") AS ?source_cfitems)
       ?target
       ?target_format
       (GROUP_CONCAT(DISTINCT(?target_comp); SEPARATOR = "&") AS ?target_comps)
       (GROUP_CONCAT(DISTINCT(?targetcfitems); SEPARATOR = "&") AS ?target_cfitems)
       WHERE
       { GRAPH <http://metarelate.net/mappings.ttl> {
           ?map mr:creator ?creator ;
                mr:creation ?creation ;
                mr:status ?status ;
                mr:reason ?reason ;
                mr:source ?source ;
                mr:target ?target .
           OPTIONAL {?map mr:owner ?owner .}
           OPTIONAL {?map mr:watcher ?watcher .}
           OPTIONAL {?map dc:replaces ?replaces .}
           OPTIONAL {?map mr:comment ?comment .}
           %s
           FILTER (?status NOT IN ("Deprecated", "Broken"))
           MINUS {?map ^dc:replaces+ ?anothermap} 
           }
           GRAPH <http://metarelate.net/concepts.ttl>{
           ?source mr:component ?source_comp ;
                   mr:format ?source_format .
           ?target mr:component ?target_comp ;
                   mr:format ?target_format .
           }
           OPTIONAL { SELECT ?source_comp (GROUP_CONCAT(?sourcecfitem; SEPARATOR = "|") as ?sourcecfitems ) 
           WHERE { GRAPH <http://metarelate.net/cflinks.ttl> {
           ?source_comp ?cfp ?cfo .
           BIND(CONCAT(STR(?cfp), ";", STR(?cfo)) AS ?sourcecfitem) } }
           GROUP BY ?source_comp }
           OPTIONAL { SELECT ?target_comp (GROUP_CONCAT(?targetcfitem; SEPARATOR = "|") as ?targetcfitems ) 
           WHERE { GRAPH <http://metarelate.net/cflinks.ttl> {
           ?target_comp ?cfp ?cfo .
           BIND(CONCAT(STR(?cfp), ";", STR(?cfo)) AS ?targetcfitem) } }
           GROUP BY ?target_comp }
           }
        GROUP BY ?map ?creator ?creation ?status ?replaces ?comment ?reason ?source ?source_format ?target ?target_format
    ''' % (search_string)
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
    results = fuseki_process.run_query(qstr, debug=debug)
    return results

###validation rules

def multiple_mappings(fuseki_process, debug=False):
    """returns all the mappings which map the same source to a different target"""
    qstr = '''SELECT ?amap ?asource ?atarget ?bmap ?bsource ?btarget
    WHERE {
    GRAPH <http://metarelate.net/mappings.ttl> {
    ?amap mr:status ?astatus ;
         mr:source ?asource ;
         mr:target ?atarget .
    FILTER (?astatus NOT IN ("Deprecated", "Broken"))
    MINUS {?amap ^dc:replaces+ ?anothermap}
    }
    GRAPH <http://metarelate.net/mappings.ttl> {
    ?bmap mr:status ?bstatus ;
         mr:source ?bsource ;
         mr:target ?btarget .
    FILTER (?bstatus NOT IN ("Deprecated", "Broken"))
    MINUS {?bmap ^dc:replaces+ ?anothermap}
    }
    GRAPH <http://metarelate.net/concepts.ttl> {
    ?asource mr:format ?asourceformat .
    ?bsource mr:format ?bsourceformat .
    ?atarget mr:format ?atargetformat .
    ?btarget mr:format ?btargetformat .
    }
    filter (?amap != ?bmap)
    filter (?asource = ?bsource)
    filter (?atarget != ?btarget)
    filter (?atargetformat = ?btargetformat)
    }
    ORDER BY ?asource
    '''
    results = fuseki_process.run_query(qstr, debug=debug)
    return results


def print_records(res):
    """ helper for command line query interpretation"""
    print_string = ''
    for r in res:
        if len(r.keys()) == 3 and r.has_key('s') and r.has_key('p') and r.has_key('o'):
            print_string += '%s\n' % r['s']
            print_string += '\t%s\n' % r['p']
            print_string += '\t\t%s\n' % r['o']
            print_string += '\n'
        else:
            for k,v in r.iteritems():
                print_string += '%s %s\n' (k, v)
            print_string += '\n'
    return print_string

