

import datetime
import glob
import time

import iris.fileformats.um_cf_map as umcf

import metocean.fuseki as fu
import metocean.queries as moq
import metocean.prefixes as prefixes

import moreumcf

gribParams = {}
end=False
with open('grib2paramrules', 'r') as gribp:
    for line in gribp.readlines():
        if line.startswith('IF'):
            container = {}
            end = False
        elif line.startswith('THEN'):
            end=False
        elif line.startswith('grib'):
            elems = line.split('==')
            container[elems[0].split('.')[1].strip()] = elems[1].strip()
        elif line.startswith('CM'):
            #CMAttribute("standard_name", "potential_temperature")
            #CMAttribute("units", "K")
            line = line.split('CMAttribute("')[1]
            line = line.split('")')[0]
            elems=line.split('", "')
            container[elems[0]] = elems[1]
        else:
            end = True
        #print container, end
        if container.has_key('standard_name') and end is True:
            if gribParams.has_key(container['standard_name']):
                raise ValueError('got this s_n')
            else:
                gribParams[container['standard_name']] = {}
                for key, elem in container.iteritems():
                    gribParams[container['standard_name']][key] = elem
            end=False

umcfdict = dict(umcf.STASH_TO_CF, **moreumcf.MOSIG_STASH_TO_CF)


linkages = []

fcuri = 'http://reference.metoffice.gov.uk/def/um/fieldcode/'



for fc,cf in umcf.LBFC_TO_CF.iteritems():
    adict = {}
    adict['cfl'] = {'mrcf:standard_name':'<http://def.cfconventions.org/standard_names/%s>' % cf[0], 'mrcf:units':'"%s"' % cf[1], 'mrcf:type':'"Field"'}
    if umcf.CF_TO_LBFC.has_key(cf) and umcf.CF_TO_LBFC[cf] == fc:
        adict['rootA'] = {'mr:rootA':['<%s%i>' % (fcuri,fc)]}
    else:
        adict['rootA'] = {'mr:rootA':['<%s%i>' % (fcuri,fc)], 'mr:direction':['"AB"']}
    adict['rootB'] = 'cfl'
    linkages.append(adict)

for cf,fc in umcf.CF_TO_LBFC.iteritems():
    if not (umcf.LBFC_TO_CF.has_key(fc) and umcf.LBFC_TO_CF[fc] == cf):
        adict = {}
        adict['cfl'] = {'mrcf:standard_name':'<http://def.cfconventions.org/standard_names/%s>' % cf[0], 'mrcf:units':'"%s"' % cf[1], 'mrcf:type':'"Field"'}
        adict['rootA'] = {'mr:rootA':['<%s%i>' % (fcuri,fc)], 'mr:direction':['"BA"']}
        adict['rootB'] = 'cfl'
        linkages.append(adict)



for stash,cf in umcfdict.iteritems():
    adict = {}
    adict['rootA'] = {'mr:rootA':['<http://reference.metoffice.gov.uk/def/um/stash/concept/%s>' % stash], 'mr:direction':['"AB"']}
    adict['rootB'] = 'cfl'
    adict['cfl'] = {'mrcf:standard_name':'<http://def.cfconventions.org/standard_names/%s>' % cf[0], 'mrcf:units':'"%s"' % cf[1], 'mrcf:type':'"Field"'}
    linkages.append(adict)

griburi = 'http://codes.wmo.int/grib2/codeflag/4.2'

for sn,gribcf in gribParams.iteritems():
    adict = {}
    adict['cfl'] = {'mrcf:standard_name':'<http://def.cfconventions.org/standard_names/%s>' % gribcf['standard_name'], 'mrcf:units':'"%s"' % gribcf['units'], 'mrcf:type':'"Field"'}
    adict['rootB'] = 'cfl'
    adict['rootA'] = {'mr:rootA':['<%s/%s/%s/%s>' % (griburi,gribcf['discipline'],gribcf['parameterCategory'],gribcf['parameterNumber'])]}
    linkages.append(adict)

adict = {} 
adict['cfl'] = {'mrcf:standard_name':'<http://def.cfconventions.org/standard_names/%s>' % 'eastward_wind', 'mrcf:units':'"%s"' % 'm s-1'}
adict['rootA'] = {'mr:rootA':['<http://reference.metoffice.gov.uk/def/um/stash/concept/%s>' % 'm01s00i002'], 'mr:direction':['"AB"']}
adict['rootB'] = 'cfl'
linkages.append(adict)

adict = {} 
adict['cfl'] = {'mrcf:standard_name':'<http://def.cfconventions.org/standard_names/%s>' % 'northward_wind', 'mrcf:units':'"%s"' % 'm s-1'}
adict['rootA'] = {'mr:rootA':['<http://reference.metoffice.gov.uk/def/um/stash/concept/%s>' % 'm01s00i003'], 'mr:direction':['"AB"']}
adict['rootB'] = 'cfl'
linkages.append(adict)


# print linkages
# print len(linkages)

# for link in linkages:
#     if link.has_key('grib'):
#         print link


#     written = '"False"'
#     for link in linkages:
#         if link.has_key('um') and link['um']['mr:UMlink'].startswith('<%s' % fcuri) and link['um']['mr:UMlink'].endswith('/%i>' % fc) and link['cfl']['mrcf:standard_name'].endswith('/%s>' % cf[0]) and link['cfl']['mrcf:units'] == cf[1]:
#             link['um']['mr:UMexport'] = '"True"'
#             written = '"True"'
#     if written == '"False"':
# #        print 'new', cf[0], cf[1], fc
#         adict = {}
#         adict['cfl'] = {'mrcf:standard_name':'<http://def.cfconventions.org/standard_names/%s>' % cf[0], 'mrcf:units':'"%s"' % cf[1], 'mrcf:type':'"Field"'}
#         adict['cf'] = {'mr:CFimport':'"True"', 'mr:CFexport':'"True"'}
#         adict['um'] = {'mr:UMlink':'<%s%i>' % (fcuri,fc), 'mr:UMimport':'"False"', 'mr:UMexport':'"True"'}
#         linkages.append(adict)

# for l in linkages:
#     if l.has_key('um') and l['um']['mr:UMimport'] is "True" and l['um']['mr:UMexport'] is "True":
#         print l

#print len(linkages)

ttl_str = '''#(C) British Crown Copyright 2011 - 2012, Met Office This file is part of metOcean-mapping.
#metOcean-mapping is free software: you can redistribute it and/or modify it under the terms of the
#GNU Lesser General Public License as published by the Free Software Foundation, either version 3 of the License,
#or (at your option) any later version. metOcean-mapping is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#See the GNU Lesser General Public License for more details. You should have received a copy of the
#GNU Lesser General Public License along with metOcean-mapping. If not, see http://www.gnu.org/licenses/." 

'''
pre = prefixes.Prefixes()

for st_file in glob.glob('/net/home/h04/itmh/metarelate/metOcean-mapping/staticData/metocean/*.ttl'):
    with open(st_file, 'w') as st:
        st.write(ttl_str)
        st.write(pre.turtle)


globalDateTime = datetime.datetime.now().isoformat()
mapping_p_o = {}
mapping_p_o['mr:owner'] = ['"None"']
mapping_p_o['mr:watcher'] = ['"None"']
mapping_p_o['mr:creator'] = ['<https://github.com/marqh>']
mapping_p_o['mr:creation'] = ['"%s"^^xsd:dateTime' % globalDateTime]
mapping_p_o['mr:status'] = ['"Draft"']
mapping_p_o['dc:replaces'] = ['"None"']
mapping_p_o['mr:comment'] = ['"Imported from external mapping resource"']
mapping_p_o['mr:reason'] = ['"new mapping"']


with fu.FusekiServer(3131) as fu_p:
    fu_p.load()

    for newlink in linkages:
        cflink = moq.create_cflink(fu_p, newlink['cfl'], 'http://www.metarelate.net/metocean/cf')
        if len(cflink) == 1:
            if newlink['rootA'] == 'cfl':
                newlink['rootA'] = {'mr:rootA':['<%s>' % cflink[0]['s']]}
            elif newlink['rootB'] == 'cfl':
                newlink['rootB'] = {'mr:rootB':['<%s>' % cflink[0]['s']]}
            else:
                print newlink
                raise ValueError('no cflink')
        else:
            raise ValueError('create_cflink failed on %s; %i cflinks retrieved' % (newlink['cfl'], len(cflink)))
#        linkage_dict = {}
#        for key in newlink.keys():
#            if key != 'cfl':
#                 linkage_dict =  dict(linkage_dict, **newlink[key])
        #linkage = moq.get_linkage(fu_p, linkage_dict)
        map_dict = mapping_p_o.copy()
        map_dict = dict(map_dict, **newlink['rootA'])
        map_dict = dict(map_dict, **newlink['rootB'])
        #if len(linkage) == 1:
        #    map_dict['mr:linkage'] = ['<%s>' % linkage[0]['linkage']]
        #else:
        #    raise ValueError('create_linkage failed on %s; %i linkages returned' % (newlink['cfl'], len(linkage)))
        
        new_mapping = moq.create_mapping(fu_p, map_dict)
    print 'saving cached changes'
    fu_p.save()



    
    
