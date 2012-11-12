
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
import fusekiQuery as query



def revert_cache(graph='http://mappings/', debug=False):
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
    results = query.run_query(qstr, update=True, debug=debug)
    return results


def save_cache(graph, debug=False):
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
    results = query.run_query(qstr, output="text", debug=debug)
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
    results = query.run_query(qstr, update=True, debug=debug)
    return results


def query_cache(graph='http://mappings/', debug=False):
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
    results = query.run_query(qstr, debug=debug)
    return results


def current_mappings(debug=False):
    '''
    return all triples currently valid in the mappings graph
    '''
    
    qstr = '''
    SELECT ?s ?p ?o
    FROM <http://mappings/>
    WHERE
    {
    ?s ?p ?o ;
        mr:status ?status.

        FILTER (?status NOT IN ("Deprecated", "Broken")) .

        {
          SELECT ?map ?previous
          WHERE
          {

           ?map mr:previous ?previous .

           MINUS {?map ^mr:previous+ ?map}
           }
        }
    }
    '''
    results = query.run_query(qstr, update=True, debug=debug)
    return results

def mapping_by_link(paramlist=False,debug=False):
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
       ?previous
       ?comment
       ?reason
       ?link
       (GROUP_CONCAT(DISTINCT(?cfitem); SEPARATOR = "&") AS ?cfelems) 
       (GROUP_CONCAT(DISTINCT(?cflink); SEPARATOR = "&") AS ?cflinks) 
       (GROUP_CONCAT(DISTINCT(?umlink); SEPARATOR = "&") AS ?umlinks)
       (GROUP_CONCAT(DISTINCT(?griblink); SEPARATOR = "&") AS ?griblinks)


    WHERE
      {
              GRAPH <http://mappings/> {
              ?cflink ?cfp ?cfo .
              BIND(CONCAT(STR(?cfp), ";", STR(?cfo)) AS ?cfitem)
              }
      { SELECT ?map ?owner ?watcher ?creator ?creation ?status ?previous ?comment ?reason ?link ?cflink ?umlink ?griblink

        WHERE { GRAPH <http://mappings/> {
           ?map mr:owner ?owner ;
                mr:watcher ?watcher ;
                mr:creator ?creator ;
                mr:creation ?creation ;
                mr:status ?status ;
                mr:previous ?previous ;
                mr:comment ?comment ;
                mr:reason ?reason ;
                mr:linkage ?link .
%s
       OPTIONAL
           {?link mr:CFlink ?cflink .         
           }
       OPTIONAL
           {?link mr:UMlink ?umlink . }
       OPTIONAL
           {?link mr:GRIBlink ?griblink .}
       
       FILTER (?status NOT IN ("Deprecated", "Broken"))
       MINUS {?map ^mr:previous+ ?map}
    } } } }
    GROUP BY ?map ?creator ?creation ?status ?previous ?comment ?reason ?link
    ''' % (linkpattern)
    results = query.run_query(qstr, debug=debug)
    return results

def fast_mapping_by_link(dataformat,linklist=False,debug=False):
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
       ?previous
       ?comment
       ?reason
       ?link
       (GROUP_CONCAT(DISTINCT(?cflink); SEPARATOR = "&") AS ?cflinks) 
       (GROUP_CONCAT(DISTINCT(?umlink); SEPARATOR = "&") AS ?umlinks)
       (GROUP_CONCAT(DISTINCT(?griblink); SEPARATOR = "&") AS ?griblinks)


    WHERE
      
 { GRAPH <http://mappings/> {
           ?map mr:owner ?owner ;
                mr:watcher ?watcher ;
                mr:creator ?creator ;
                mr:creation ?creation ;
                mr:status ?status ;
                mr:previous ?previous ;
                mr:comment ?comment ;
                mr:reason ?reason ;
                mr:linkage ?link .
%s
       OPTIONAL
           {?link mr:CFlink ?cflink .         
           }
       OPTIONAL
           {?link mr:UMlink ?umlink . }
       OPTIONAL
           {?link mr:GRIBlink ?griblink .}
       
       FILTER (?status NOT IN ("Deprecated", "Broken"))
       MINUS {?map ^mr:previous+ ?map}
    }}
    GROUP BY ?map ?creator ?creation ?status ?previous ?comment ?reason ?link
    ''' % (linkpattern)
    results = query.run_query(qstr, debug=debug)
    return results




def select_graph(graph, debug=False):
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
    results = query.run_query(qstr, debug=debug)
    return results


def counts_by_graph(graph, debug=False):
    #deprecated
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
    results = query.run_query(qstr)
    return results

def count_by_graph(debug=False):
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
    results = query.run_query(qstr)
    return results



def subject_by_graph(graph, debug=False):
    '''
    selects distinct subject from a particular graph
    '''
    #used in listtype
    qstr = '''
        SELECT DISTINCT ?subject
        WHERE {
            GRAPH <%s> { ?subject ?p ?o } .
        }
        ORDER BY ?subject

    ''' % graph
    
    results = query.run_query(qstr, debug=debug)
    return results

def subject_graph_pattern(graph,pattern,debug=False):
    '''
    selects distinct subject from a particular graph matching a pattern
    '''
    #used in listtype
    qstr = '''
        SELECT DISTINCT ?subject
        WHERE {
            GRAPH <%s> { ?subject ?p ?o } .
            FILTER( REGEX(str(?subject), '%s') ) .            
        }
        ORDER BY ?subject

    ''' % (graph,pattern)
    
    results = query.run_query(qstr, debug=debug)
    return results
    



def get_cflink_by_id(cflink, debug=False):
    '''
    return a cflink record, if one exists, using the MD5 ID
    '''
    qstr = '''
    SELECT ?type ?standard_name ?units ?long_name
    FROM <http://mappings/>
    WHERE
    {
    ?s mrcf:type ?type .
    OPTIONAL
    { ?s mrcf:standard_name ?standard_name .}
    OPTIONAL
    { ?s mrcf:units ?units . }
    OPTIONAL
    { ?s mrcf:long_name ?long_name . }
    FILTER (?s = <%s>)
    }
    ''' % cflink
    results = query.run_query(qstr, debug=debug)

    return results

def get_cflinks(pred_obj=None, debug=False):
    '''
    return cflink records matching the predicate object dictionary items
    '''
    filterstr = ''
    if pred_obj:
        for key in pred_obj.keys():
#        if pred_obj.has_key('standard_name'):
            filterstr += '''FILTER (bound(?%s))
            FILTER (regex(str(?%s), str(%s), "i"))
            ''' % (key.split(':')[1],key.split(':')[1],pred_obj[key])
    qstr  = '''
    SELECT ?s ?type ?standard_name ?units ?long_name
    FROM <http://mappings/>
    WHERE
    {
    ?s mrcf:type ?type .
    OPTIONAL
    { ?s mrcf:standard_name ?standard_name .}
    OPTIONAL
    { ?s mrcf:units ?units . }
    OPTIONAL
    { ?s mrcf:long_name ?long_name . }
    %s
    }
    ''' % filterstr 
    results = query.run_query(qstr, debug=debug)

    return results


def get_by_attrs(po_dict, debug=False):
    '''
    return records, if they exists, using the dictionary of predicates and lists of objects
    a list of triple dictionaries is returned.  The list is ordered by subject, but no grouping is explicit in the list.

    '''
    pred_obj = ''
    for pred, obj in po_dict.iteritems():
        #for ob in obj:
        # if po_dict[pred].split('//')[0] == 'http:':
        #     po_dict[pred] = '<%s>'% po_dict[pred]
        # else:
        #     po_dict[pred] = '"%s"'% po_dict[pred]
        pattern_string = ''';
        %s %s ''' % (pred, po_dict[pred])
        pred_obj += pattern_string

    qstr = '''
    SELECT ?s ?p ?o
    FROM <http://mappings/>
    WHERE
    {
    ?s ?p ?o
    %s
    .
    }
    ''' % pred_obj
    results = query.run_query(qstr, debug=debug)
    return results


def create_cflink(po_dict, subj_pref, debug=False):
    '''
    create a new link, using the provided predicates:objectsList dictionary, if one does not already exists.
    if one already exists, use this in preference
    subj_pref is the prefix for the subject, e.g. http://www.metarelate.net/metocean/cf, http://www.metarelate.net/metocean/linkage
    '''

    mmd5 = hashlib.md5()
    
    for pred in po_dict.keys():
#        for obj in po_dict[pred]:
        mmd5.update(pred)
        mmd5.update(po_dict[pred])

    md5 = str(mmd5.hexdigest())
    #ask yourself whether you want to calculate the MD5 here and use it to test, or whether to pass the predicates and objects to SPARQL to query
    #current_cflink = get_cflink_by_id(md5)
    current_link = get_by_attrs(po_dict)
    if len(current_link) == 0:
        pred_obj = ''
        for pred in po_dict.keys():
#            for obj in po_dict[pred]:
            # if po_dict[pred].split('//')[0] == 'http:':
            #     po_dict[pred] = '<%s>'% po_dict[pred]
            # else:
            #     po_dict[pred] = '"%s"'% po_dict[pred]
            pattern_string = ''' %s %s ;
            ''' % (pred, po_dict[pred])
            pred_obj += pattern_string
        qstr = '''
        INSERT DATA
        { GRAPH <http://mappings/>
        { <%s/%s> %s
        mr:saveCache "True" .
        }
        }
        ''' % (subj_pref, md5, pred_obj)
        results = query.run_query(qstr, update=True, debug=debug)
        current_link = get_cflinks(po_dict)
    return current_link
    # elif len(current_cflink) ==1:
    #     md5 = md5
    # else:
    #     md5 = None
    # return md5


def get_linkage(fso_dict, debug=False):
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
            mr:%slink %s ;''' % (fstring.upper(), obj)
    if search_string != '':
        search_string += '.'
        qstr = '''
        SELECT ?linkage
            (GROUP_CONCAT(DISTINCT(?cflink); SEPARATOR = "&") AS ?cflinks) 
            (GROUP_CONCAT(DISTINCT(?umlink); SEPARATOR = "&") AS ?umlinks)
            (GROUP_CONCAT(DISTINCT(?griblink); SEPARATOR = "&") AS ?griblinks)

        WHERE
        { GRAPH <http://mappings/>{
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

        results = query.run_query(qstr, debug=debug)
        if len(results) == 1 and results[0] == {}:
            pre = prefixes.Prefixes()
            mmd5 = hashlib.md5()
            pred_obj = ''
            for format,objects in fso_dict.iteritems():
                for obj in objects:
                    (pre['mr'], format, obj)
                    mmd5.update('%s%slink' % (pre['mr'], format))
                    mmd5.update(obj)

            md5 = str(mmd5.hexdigest())

            inststr = '''
            INSERT DATA
            { GRAPH <http://mappings/>
            { <%s/%s> %s
            mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, md5, search_string.rstrip('.'))
            #print qstr
            insert_results = query.run_query(inststr, update=True, debug=debug)
            results = query.run_query(qstr, debug=debug)
    else:
        results = []

    return results



def create_mapping(po_dict, debug=False):
    '''
    create a new mapping record from a dictionary of predicates and lists of objects
    '''
    subj_pref = 'http://www.metarelate.net/metocean/mapping'
    results = None
    pre = prefixes.Prefixes()

    if po_dict.has_key('owner') and \
        po_dict.has_key('watcher') and \
        po_dict.has_key('creator') and len(po_dict['creator'])==1 and \
        po_dict.has_key('status') and len(po_dict['status'])==1 and \
        po_dict.has_key('previous') and len(po_dict['previous'])==1 and \
        po_dict.has_key('comment') and len(po_dict['comment'])==1 and \
        po_dict.has_key('reason') and len(po_dict['reason'])==1 and \
        po_dict.has_key('linkage') and len(po_dict['linkage'])==1:
        
        mmd5 = hashlib.md5()

        pred_obj = ''
        for pred,objects in po_dict.iteritems():
            for obj in objects:
#        for pred in po_dict.keys():
#            for obj in po_dict[pred]:
                pattern_string = ''' mr:%s %s ;
                ''' % (pred, obj)
                pred_obj += pattern_string
                if pred != 'creation':
                    mmd5.update('%s%s' % (pre['mr'], pred))
                    mmd5.update(obj)

        md5 = str(mmd5.hexdigest())
        # check if we already have one:
        result = subject_graph_pattern('http://mappings/',
                'http://www.metarelate.net/metocean/mapping/%s' % md5)
        if len(result) == 0:
            qstr = '''
            INSERT DATA
            { GRAPH <http://mappings/>
            { <%s/%s> %s
            mr:saveCache "True" .
            }
            }
            ''' % (subj_pref, md5, pred_obj)
            results = query.run_query(qstr, update=True, debug=debug)
    return results


def get_contacts(register, debug=False):
    '''
    return a list of contacts from the tdb which are part of the named register 
    '''
    qstr = '''
    SELECT ?s
    WHERE
    {GRAPH <http://contacts/>{
        ?s iso19135:definedInRegister ?register .
           OPTIONAL{
               ?s mr:retired ?retired}
               }
    FILTER (!bound(?retired))
    FILTER (regex(str(?register),"%s", "i"))
    }
    ''' % register
    results = query.run_query(qstr, debug=debug)
    return results

def create_contact(register, contact, creation, debug=False):
    '''
    create a new contact
    '''
    qstr = '''
    INSERT DATA
    {
    %s a mr:contact ;
    iso19135:definedInRegister %s ;
    mr:creation "%s"^^xsd:dateTime .
    }
    ''' % (contact, register, creation)
    results = query.run_query(qstr, debug=debug)
    return results

    
        
    
# def (, debug=False):
#     '''
#     '''
#     qstr = '''
#     '''
#     results = query.run_query(qstr, debug=debug)
#     return results

def export_linkages(debug=False):
    '''
    '''
    qstr = '''SELECT ?linkage ?UMlink ?CFlink ?GRIBlink
    WHERE
    { GRAPH <http://mappings/> {
    ?linkage mr:UMlink <http://reference.metoffice.gov.uk/data/stash/m01s00i003/vn8.2> .
     OPTIONAL{
     ?linkage mr:UMlink ?UMlink . }
     OPTIONAL{
     ?linkage mr:CFlink ?CFlink . }
     OPTIONAL{
     ?linkage mr:GRIBlink ?GRIBlink . }
        }
    } 
    '''
    results = query.run_query(qstr, debug=debug)
    return results


def export_mappings(debug=False):
    '''
    '''
    qstr = '''SELECT ?map ?status ?comment ?reason ?owner ?watcher ?creator ?created ?replaces ?linkage 
    WHERE
    { GRAPH <http://mappings/> {
     ?map mr:linkage ?link ; 
           mr:owner ?owner ;
           mr:watcher ?watcher ;
           mr:creation ?created ;
           mr:status ?status ;
           mr:reason ?reason ;
           mr:comment ?comment ;
           mr:previous ?replaces ;
           mr:linkage ?linkage .
     ?linkage mr:UMlink <http://reference.metoffice.gov.uk/data/stash/m01s00i003/vn8.2> .
    BIND(<https://github.com/marqh> as ?creator)
        }

    }
    '''

    # qstr = '''SELECT ?map ?linkage 
    # WHERE
    # { GRAPH <http://mappings/> {
    #  ?map  mr:linkage ?linkage .
    #  ?linkage mr:UMlink <http://reference.metoffice.gov.uk/data/stash/m01s00i003/vn8.2> .
    #     }

    # }
    # '''
    results = query.run_query(qstr, debug=debug)
    return results

def print_records(res):
    for r in res:
        for k,v in r.iteritems():
            print k, '  ', v

