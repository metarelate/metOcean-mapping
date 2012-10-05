import metocean.prefixes
import fusekiQuery as query


def revert_cache(graph):
    '''
    update a graph in the triple database removing all shards flagged with the saveCache predicate
    '''
    qstr = '''
    DELETE
    FROM <%s>
    {
        ?s ?p ?o .
    }
    WHERE
    {
    ?s ?p ?o ;
        mr:saveCache "True" .
    } 
    ''' % graph
    results = query.run_query(qstr, update=True)
    return results


def save_cache(graph):
    '''
    export new records from a graph in the triple store to an external location, as flagged by the manager application
    '''
    qstr = '''
    CONSTRUCT
    FROM <%s>
    {
        ?s ?p ?o .
    }
    WHERE
    {
    ?s ?p ?o ;
        metExtra:saveCache "True" .
    } 
    ''' % graph
    results = query.run_query(qstr, output="text")
    return results

def clear_cache(graph):
    '''
    clear the 'not saved' flags on records, updating a graph in the tiple store with the fact that changes have been persisted to ttl 
    '''
    qstr = '''
    DELETE
    FROM <%s>
    {
        ?s metExtra:saveCache "True" .
    }
    WHERE
    {
    ?s ?p ?o ;
        metExtra:saveCache "True" .
    } 
    ''' % graph
    results = query.run_query(qstr, update=True)
    return results

def select_graph(graph):
    '''
    selects a particular graph from the TDB
    '''
    #used in 'list'
    qstr = '''
        SELECT DISTINCT ?g
        WHERE {
            GRAPH ?g { ?s ?p ?o } .
            FILTER( REGEX(str(?g), 'http://%s/') ) .
        }

    ''' % graph
    results = query.run_query(qstr)
    return results


def subject_by_graph(graph):
    '''
    selects distinct subject from a particular graph
    '''
    #used in listtype
    qstr = '''
        SELECT DISTINCT ?subject
        WHERE {
            GRAPH <%s> { ?subject ?p ?o } .
            FILTER( ?p != mos:header )
        }
        ORDER BY ?subject

    ''' % graph
    results = query.run_query(qstr)
    return results

def insert_link(link_dict):
    '''
    take a dictionary of linkage values and insert into the tdb
    '''
    qstr = '''
    INSERT DATA {
    }
    '''
    results = query.run_query(qstr)
    return results

def insert_cf(cf_dict):
    '''
    insert a new cf record 
    '''
    qstr = '''
    INSERT DATA {
    }
    '''
    results = query.run_query(qstr)
    return results

# def ():
#     '''
#     '''
#     qstr = '''
#     '''
#     results = query.run_query(qstr)
#     return results

# def ():
#     '''
#     '''
#     qstr = '''
#     '''
#     results = query.run_query(qstr)
#     return results
