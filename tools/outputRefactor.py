import metOceanPrefixes as prefixes

import fusekiQuery as query


conQuery = '''
CONSTRUCT
{

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


}
'''

print conQuery
