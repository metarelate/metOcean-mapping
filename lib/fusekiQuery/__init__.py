
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


from urllib import urlencode
from urllib2 import urlopen, Request, ProxyHandler, build_opener, install_opener, URLError
import json

import metocean.prefixes as prefixes

def run_query(query_string, output='json', update=False):
    # use null ProxyHandler to ignore proxy for localhost access
    proxy_support = ProxyHandler({})
    opener = build_opener(proxy_support)
    install_opener(opener)
    pre = prefixes.Prefixes()
    if update:
        action = 'update'
        qstr = urlencode([
            (action, "%s %s" % (pre.sparql, query_string))])
    else:
        action = 'query'
        qstr = urlencode([
            (action, "%s %s" % (pre.sparql, query_string)),
            ("output", output),
            ("stylesheet","/static/xml-to-html-links.xsl")])

    BASEURL="http://127.0.0.1:3131/metocean/%s?" % action
    data = ''
    try:
        data = opener.open(Request(BASEURL), qstr).read()
    except URLError:
        raise Exception("Unable to contact Fuseki server on %s" % BASEURL)
    if output == "json":
        return process_data(data)
    elif output == "text":
        return data
    else:
        return data

def process_data(jsondata):
    resultslist = []
    try:
        jdata = json.loads(jsondata)
    except (ValueError, TypeError):
        return resultslist
    vars = jdata['head']['vars']
    data = jdata['results']['bindings']
    for item in data:
        tmplist = {}
        for var in vars:
            tmpvar = item.get(var)
            if tmpvar:
                tmplist[var] = tmpvar.get('value')
        resultslist.append(tmplist)
    return resultslist

