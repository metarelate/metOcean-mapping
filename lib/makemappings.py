
import copy
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
    adict['mr:target'] = {'mr:format':['<http://metarelate.net/metocean/format/cf>'],
                       'skos:member':[{'mr:name':'cfm:standard_name', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfsn:%s' % cf[0]},
                    {'mr:name':'cfm:units', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'"%s"' % cf[1]},
                    {'mr:name':'cfm:type', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfm:Field'}]}
    if umcf.CF_TO_LBFC.has_key(cf) and umcf.CF_TO_LBFC[cf] == fc:
        adict['mr:invertible'] = '"True"'
    else:
        adict['mr:invertible'] = '"False"'
    adict['mr:source'] = {'skos:member':[{'mr:name':'moumdpF3:lbfc', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'mofc:%i' % fc}],
                       'mr:format':['<http://metarelate.net/metocean/format/um>']}
    linkages.append(adict)

for cf,fc in umcf.CF_TO_LBFC.iteritems():
    if not (umcf.LBFC_TO_CF.has_key(fc) and umcf.LBFC_TO_CF[fc] == cf):
        adict = {}
        adict['mr:source'] = {'mr:format':['<http://metarelate.net/metocean/format/cf>'],
                       'skos:member':[{'mr:name':'cfm:standard_name', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfsn:%s' % cf[0]},
                    {'mr:name':'cfm:units', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'"%s"' % cf[1]},
                    {'mr:name':'cfm:type', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfm:Field'}]}
        adict['mr:target'] = {'skos:member':[{'mr:name':'moumdpF3:lbfc', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'mofc:%i' % fc}],
                           'mr:format':['<http://metarelate.net/metocean/format/um>']}
        adict['mr:invertible'] = '"False"'
        linkages.append(adict)



for stash,cf in umcfdict.iteritems():
    adict = {}
    adict['mr:target'] = {'mr:format':['<http://metarelate.net/metocean/format/cf>'],
                       'skos:member':[{'mr:name':'cfm:standard_name', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfsn:%s' % cf[0]},
                    {'mr:name':'cfm:units', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'"%s"' % cf[1]},
                    {'mr:name':'cfm:type', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfm:Field'}]}
    adict['mr:invertible'] = '"False"'
    adict['mr:source'] = {'skos:member':[{'mr:name':'moumdpF3:stash', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'moStCon:%s' % stash}],
                       'mr:format':['<http://metarelate.net/metocean/format/um>']}
    linkages.append(adict)

#griburi = 'http://codes.wmo.int/grib/2/codeflag/4.2'

for sn,gribcf in gribParams.iteritems():
    adict = {}
    adict['mr:target'] = {'mr:format':['<http://metarelate.net/metocean/format/cf>'],
                       'skos:member':[{'mr:name':'cfm:standard_name', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfsn:%s' % gribcf['standard_name']},
                    {'mr:name':'cfm:units', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'"%s"' % gribcf['units']},
                    {'mr:name':'cfm:type', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfm:Field'}]}
    adict['mr:invertible'] = '"True"'
    adict['mr:source'] = {'skos:member':[{'mr:name':'gribapi:edition', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'2'},
                                         {'mr:name':'gribapi:discipline', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'%s' % gribcf['discipline']},
                                         {'mr:name':'gribapi:parameterCategory', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'%s' % gribcf['parameterCategory']},
                                         {'mr:name':'gribapi:parameterNumber', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'%s' % gribcf['parameterNumber']}],
                       'mr:format':['<http://metarelate.net/metocean/format/grib>']}
    linkages.append(adict)
    

adict = {}
adict['mr:target'] = {'mr:format':['<http://metarelate.net/metocean/format/cf>'],
                       'skos:member':[{'mr:name':'cfm:standard_name', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfsn:%s' % 'eastward_wind'},
                    {'mr:name':'cfm:units', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'"%s"' % 'm s-1'},
                    {'mr:name':'cfm:type', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfm:Field'}]}
adict['mr:source'] = {'skos:member':[{'mr:name':'moumdpF3:stash', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'moStCon:%s' % 'm01s00i002'}],
                       'mr:format':['<http://metarelate.net/metocean/format/um>']}
adict['mr:invertible'] = '"False"'
linkages.append(adict)

adict = {}
adict['mr:target'] = {'mr:format':['<http://metarelate.net/metocean/format/cf>'],
                       'skos:member':[{'mr:name':'cfm:standard_name', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfsn:%s' % 'northward_wind'},
                    {'mr:name':'cfm:units', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'"%s"' % 'm s-1'},
                    {'mr:name':'cfm:type', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfm:Field'}]}
adict['mr:source'] = {'skos:member':[{'mr:name':'moumdpF3:stash', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'moStCon:%s' % 'm01s00i003'}],
                       'mr:format':['<http://metarelate.net/metocean/format/um>']}
adict['mr:invertible'] = '"False"'
linkages.append(adict)


# print linkages
# print len(linkages)


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

for st_file in glob.glob('/net/home/h04/itmh/metarelate/metOcean-mapping/staticData/metarelate.net/*.ttl'):
    if st_file.split('/')[-1] != 'contacts.ttl':
        with open(st_file, 'w') as st:
            st.write(ttl_str)
            st.write(pre.turtle)


globalDateTime = datetime.datetime.now().isoformat()
mapping_p_o = {}
mapping_p_o['dc:creator'] = ['<https://github.com/marqh>']
mapping_p_o['dc:date'] = ['"%s"^^xsd:dateTime' % globalDateTime]
mapping_p_o['mr:status'] = ['"Draft"']
mapping_p_o['skos:note'] = ['"Imported from external mapping resource: Iris 1.1"']
mapping_p_o['mr:reason'] = ['"new mapping"']


    # adict['mr:target'] = {'mr:format':['<http://metarelate.net/metocean/format/cf>'],
    #                    'skos:member':[{'mr:name':'cfm:standard_name', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfsn:%s' % cf[0]},
    #                 {'mr:name':'cfm:units', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'"%s"' % cf[1]},
    #                 {'mr:name':'cfm:type', 'mr:operator':'<http://www.openmath.org/cd/relation1.xhtml#eq>', 'rdf:value':'cfm:Field'}]}

with fu.FusekiServer(3131) as fu_p:
    fu_p.load()
    print 'load complete'
    for newlink in linkages:
        map_dict = copy.deepcopy(mapping_p_o)
        map_dict['mr:invertible'] = newlink['mr:invertible']
        st = ['mr:source', 'mr:target']
        for pref in st:
            members = newlink[pref]['skos:member']
            memberids = []
            for v_dict in members:
                prop_res = moq.get_property(fu_p, v_dict)
                if prop_res:
                    prop_id = '%s' % prop_res['property']
                else:
                    raise ValueError('%i results returned from get_value %s' % (len(val_res), str(val_res)))
                memberids.append(prop_id)
            fc_dict = {'mr:format' : newlink[pref]['mr:format'],
                       'skos:member' : memberids}
            fc_res = moq.get_format_concept(fu_p, fc_dict)
            if fc_res:
                fcID = '%s' % fc_res['formatConcept']
            else:
                raise ValueError('%i results returned from get_format_concept %s' % (len(fc_res), str(fc_res)))
            map_dict[pref] = fcID
        map_res = moq.create_mapping(fu_p, map_dict)
    print 'saving cached changes'
    fu_p.save()

