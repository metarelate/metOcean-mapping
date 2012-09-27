import metOceanPrefixes as prefixes

import fusekiQuery as query

import hashlib
import os
import sys

def FileHash(file):
    '''large file md5 hash generation'''
    md5 = hashlib.md5()
    with open(file,'rb') as f: 
        for chunk in iter(lambda: f.read(8192), b''): 
             md5.update(chunk)
    return md5.hexdigest()



'''
MapQuery takes all of the contents of the repository's mapping and linkage shards and exports them unchanged, recomputing the MD5 sums

A version of this may be adapted by changing the construct statement to output a new shard design

if this is done, this script must be updated, changing the where and construct clauses, to match the new shard design
'''

mapQuery = '''
CONSTRUCT
{
?newMap
    metExtra:hasOwner ?owner ;
    metExtra:hasWatcher ?watcher ;
    metExtra:hasEditor ?editor ;
    metExtra:hasStatus ?status ;
    metExtra:hasPrevious ?previous ;
    metExtra:hasLastEdit ?editTime ;
    metExtra:hasComment ?comment ;
    metExtra:hasReason ?reason ;
    metExtra:link ?newLink .
?newLink
    metExtra:origin ?origin ;
    cf:units ?units ;
    metExtra:long_name ?longName ;
    cf:name ?name .

}
WHERE
{
?s  metExtra:hasOwner ?owner ;
    metExtra:hasWatcher ?watcher ;
    metExtra:hasEditor ?editor ;
    metExtra:hasStatus ?status ;
    metExtra:hasPrevious ?previous ;
    metExtra:hasLastEdit ?editTime ;
    metExtra:hasComment ?comment ;
    metExtra:hasReason ?reason ;
    metExtra:link ?link .
?link
    metExtra:origin ?origin ;
    cf:units ?units ;
    metExtra:long_name ?longName ;
    cf:name ?name .

BIND (md5(concat(str(?origin),?longName,?units,str(?name))) as ?linkMD5)
BIND (URI(CONCAT("http://www.metarelate.net/metOcean/linkage/",?linkMD5)) as ?newLink)
    
BIND (md5(concat(?owner,?watcher,?editor,?status,str(?previous),?comment,?reason,str(?link))) as ?mapMD5)
BIND (URI(CONCAT("http://www.metarelate.net/metOcean/mapping/",?mapMD5)) as ?newMap)
}
'''





newMappings = query.run_query(mapQuery, output='text')



tfile = '../default/contmp.ttl'


temp = open(tfile, 'w')

temp.write(newMappings)

temp.close()


md5 = str(FileHash(tfile))

os.rename(tfile, '../default/%s' % md5)

