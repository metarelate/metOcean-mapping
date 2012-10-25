# Python module to hold the master references for MetOcean Metadata Translation prefixes

import StringIO
import re


class Prefixes(dict):
    __slots__ = []
    
    def __init__(self):
        #super(Prefixes, self).__init__()
        prefixd = {
        'rdfs'     : 'http://www.w3.org/2000/01/rdf-schema#',
        'rdf'      : 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'skos'     : 'http://www.w3.org/2004/02/skos/core#',
        'xsd'      : 'http://www.w3.org/2001/XMLSchema#',
        'iso19135' : 'http://reference.metoffice.gov.uk/data/wmo/def/iso19135/',
        'metExtra' : 'http://reference.metoffice.gov.uk/data/wmo/def/met/',
        'mos'      : 'http://reference.metoffice.gov.uk/data/stash/',
        'mof'      : 'http://reference.metoffice.gov.uk/data/fieldcode/',
        'mon'      : 'http://reference.metoffice.gov.uk/data/none/',
        'map'      : 'http://www.metarelate.net/metOcean/mapping/',
        'link'     : 'http://www.metarelate.net/metOcean/linkage/',
        'fcode'    : 'http://www-hc/~umdoc/pp_package_ibm_docs/fcodes/',
        'cf'       : 'http://cf-pcmdi.llnl.gov/documents/',
        'mr'       : 'http://www.metarelate.net/predicates/index.html#',
        'mrcf'     : 'http://www.metarelate.net/predicates/CF.html#',
        'github'   : 'https://github.com/' ,
        'metoc'    : 'http://www.metarelate.net/metOcean/' , 
        }
        self.update(prefixd)

    def __getattr__(self, key):
        return self[key]

    def value2key(self, value):
        for k, v in self.items():
           if v == value:
                return k 

    @property
    def sparql(self):
        ios = StringIO.StringIO()
        for key, value in sorted(self.items()):
            ios.write('PREFIX %s: <%s>\n' % (key, value))
        ios.write('\n')
        return ios.getvalue()

    @property
    def turtle(self):
        ios = StringIO.StringIO()
        for key, value in sorted(self.items()):
            ios.write('@prefix %s: <%s> .\n' % (key, value))
        ios.write('\n')
        return ios.getvalue()

    @property
    def rdf(self):
        ios = StringIO.StringIO()
        for key, value in sorted(self.items()):
            ios.write('xmlns:%s="%s"\n' % (key, value))
        ios.write('\n')
        return ios.getvalue()

    @property
    def irilist(self):
        return sorted(self.values())

    @property
    def datalist(self):
        return sorted([(x,y) for x,y in self.items() if not re.search('#$', y)])

    @property
    def prefixlist(self):
        return sorted(self.keys())


