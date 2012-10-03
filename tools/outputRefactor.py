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
MapQuery takes all of the contents of the repository's mapping and linkage recors and exports them refactored using construct, recomputing the MD5 sums

'''

mapQuery = '''
CONSTRUCT
{
?newMap
    mr:owner ?owner ;
    mr:watcher ?watcher ;
    mr:editor ?editor ;
    mr:status ?status ;
    mr:previous ?previous ;
    mr:creation ?editTime ;
    mr:comment ?comment ;
    mr:reason ?reason ;
    mr:link ?newLink .
?newLink
    mr:UMlink ?origin ;
    mr:CFlink ?newCF .
?newCF
    mrcf:units ?units ;
    mrcf:long_name ?longName ;
    mrcf:standard_name ?name .

}
WHERE
{
?map
    metExtra:hasOwner ?owner ;
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

MINUS {?link cf:name <http://reference.metoffice.gov.uk/data/none/none>}


BIND (md5(concat(?longName,?units,str(?name))) as ?cfMD5)
BIND (URI(CONCAT("http://www.metarelate.net/metOcean/CF/",?cfMD5)) as ?newCF)

BIND (md5(concat(str(?origin),str(?newCF))) as ?linkMD5)
BIND (URI(CONCAT("http://www.metarelate.net/metOcean/linkage/",?linkMD5)) as ?newLink)
    
BIND (md5(concat(?owner,?watcher,?editor,?status,str(?previous),?comment,?reason,str(?newLink))) as ?mapMD5)
BIND (URI(CONCAT("http://www.metarelate.net/metOcean/mapping/",?mapMD5)) as ?newMap)

}
'''





newMappings = query.run_query(mapQuery, output='text')



tfile = '../staticData/default/contmp.ttl'

license = '''(C) British Crown Copyright 2011 - 2012, Met Office This file is part of metOcean-mapping. metOcean-mapping is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. metOcean-mapping is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details. You should have received a copy of the GNU Lesser General Public License along with metOcean-mapping. If not, see http://www.gnu.org/licenses/." 


'''

temp = open(tfile, 'w')

temp.write
temp.write(newMappings)

temp.close()


md5 = str(FileHash(tfile))

os.rename(tfile, '../staticData/default/%s.ttl' % md5)

