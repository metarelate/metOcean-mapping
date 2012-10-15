
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


# Create your views here.
import sys
import os
import re
import urllib
import itertools 
import datetime
import hashlib

import forms
import fusekiQuery as query

import metocean.prefixes as prefixes
import metocean.queries as moq

from settings import READ_ONLY

from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.utils.safestring import mark_safe
from django.forms.formsets import formset_factory
from django.forms.models import inlineformset_factory

def contact(request, contact_id):
    pass


def contacts(request):
    pass


def provenance(request, provenance_id):
    pass


def provenances(request):
    # report in column view
    pass

def supported_datatypes():
    SUPPORTED_DATATYPES = (
        'UM',
        'GRIB',
        'CF'
        )
    return SUPPORTED_DATATYPES




def count_by_group(results, keyfunc):
    '''perform a grouped-summation based upon the provided callback.'''
    uniquetype = {}
    for k, g in itertools.groupby(results, keyfunc):
        uniquetype[k] = reduce(lambda x,y: int(x) + int(y), [x.get('count') for x in g], 0)
    return uniquetype

def split_by_datatype(name):
    return name.split('.')[0]

def split_by_type(item):
    name = item.get('g').split('/')[2]
    return split_by_datatype(name)


def split_by_localname(item):
    name = item.get('g').split('/')[-1]
    return name

def formats(request):
    '''Top-level view.
    This provides a list of the known 'data types' and  count of records found within each.
    this view links to the 'list' view
    '''
    
    itemlist = []
    resultsd = count_by_group(moq.count_by_graph(), split_by_type)
    for item in supported_datatypes():
        name = item.lower()
        itemlist.append( {
            'url' : reverse('list_format', kwargs={'dataFormat' : name}),
            'label' : item, 
            'count' : resultsd.get(name, 0),
        } )
    context = RequestContext(request, {
            'title' : 'Formats',
            'itemlist' : itemlist,
            }) 
     
    return render_to_response('formats.html', context)
        
def url_with_querystring(path, **kwargs):
    return path + '?' + urllib.urlencode(kwargs)

def list_format(request, dataFormat):
    '''First level of detail.
    This view expands the chosen 'dataFormat' and displays all known subgraphs within it,
    along with counts of records within each subgraph.
    this view links to the 'listtype' view
    '''
    graph = 'http://%s/' % dataFormat
    results = moq.select_graph(graph)
    itemlist = []
    count_results = moq.counts_by_graph(graph)
    dataFormat_resultsd = count_by_group(count_results, split_by_type)
    for item in results:
        url = reverse('listtype', kwargs={
            'dataFormat' : dataFormat, 'datatype':split_by_localname(item) })
        itemlist.append({
            'url'   : url, 
            'label' : '%s' % item.get('g'), 
            'count' : count_by_group(count_results, 
                lambda x:x.get('g')).get(item.get('g')),
        })
    context = RequestContext(request, {
            'title' : dataFormat.upper(),
            'viewname' : 'List Format',
            'itemlist' : sorted(itemlist, key=lambda x:x['label']),
            'read_only' : READ_ONLY,
            'count' : 'Records: %s' % dataFormat_resultsd.get(dataFormat),
            })  
    return render_to_response('list_formats.html', context)
        

def listtype(request, dataFormat, datatype):
    '''Second level of detail.
    This view lists the records actually contained within the named graph
    and display the count.
    this view links to the 'edit' or 'new' views
    '''
    
    graph = 'http://%s/%s' % (dataFormat,datatype)

    results = moq.subject_by_graph(graph)
    type_resultsd = count_by_group(moq.count_by_graph(), split_by_type)
    itemlist = []
    for item in [x.get('subject') for x in results]:
        itemlist.append({
            'url'   : url_with_querystring(
                        reverse('edit', kwargs={'dataFormat':dataFormat,'datatype' : datatype}),
                        ref=item),
            'label' : item,
        })
    context = RequestContext(request, {
            'viewname' : 'Listing',
            'detail' : 'Datatype: %s' % datatype,
            'itemlist' : itemlist,
            'read_only' : READ_ONLY,
            'count' : 'Records: %s' % type_resultsd.get(split_by_datatype(datatype)),
            'newrecord' : reverse('newrecord', kwargs={'dataFormat' : dataFormat,'datatype' : datatype}),
            }) 


    return render_to_response('main.html', context)

def newrecord(request, dataFormat, datatype):
    '''form view to create a new record'''
    MappingFormSet = formset_factory(forms.MappingNewForm, extra=0)
    if request.method == 'POST':
        formset = MappingFormSet(request.POST)
        if formset.is_valid():
            pass
    else:
        record = request.GET.get('ref', '')
        record = urllib.unquote(record).decode('utf8')

        formset = MappingFormSet(initial=[
            {
            'current_status' : 'draft',
            'last_edit' : datetime.datetime.now(),
            }])
    return render_to_response('main.html',
        RequestContext(request, {
            'title' : 'New record',
            'viewname' : 'New record',
            'detail' : 'Datatype: %s' % datatype,
            'read_only' : READ_ONLY,
            'formset' : formset,
            }) )

def edit(request, dataFormat, datatype):
    '''form view to edit one or more records, retrieved based on a format specific request'''
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    search_path = [request_search_path]
    pre = prefixes.Prefixes()

    MappingFormSet = formset_factory(forms.MappingEditForm, extra=0)
    warning_msg = ''
    if request.method == 'POST':
        formset = MappingFormSet(request.POST)
        if formset.is_valid():
            process_formset(formset, request)
            return HttpResponseRedirect(
                url_with_querystring(
                    reverse('edit', kwargs={'dataFormat':dataFormat,'datatype' : datatype}),
                    ref=request_search_path))
        else:
            print formset.errors
    else:
        urecordm = moq.mapping_by_link(dataFormat,search_path)
        if len(urecordm) > 1:
            warning_msg = (
                'Warning: '
                '%s Active Data Records with the same format pattern found.' %
                (len(urecordm)))
        initial_data_set = []
        for item in urecordm:
            data_set = {}
            mapurl = item.get('map')
            previousurl = item.get('previous')
            previouslabel = previousurl.split('/')[-1]
            data_set = dict(
                mapping = item.get('map'),
                linkage = item.get('link'),
                last_edit = item.get('creation'),
                last_editor = item.get('creator'),
                current_status = item.get('status'),
                last_comment = item.get('comment'),
                last_reason = item.get('reason'),
                owners = item.get('owners'),
                watchers = item.get('watchers'),
                previous = mark_safe("%s" % previouslabel),
                cflinks = item.get('cflinks'),
                umlinks = item.get('umlinks'),
                griblinks = item.get('griblinks')
                )
            initial_data_set.append(data_set)
        formset = MappingFormSet(initial=initial_data_set)
    return render_to_response('main.html',
        RequestContext(request, {
            'viewname' : 'Edit Record',
            'title' : 'Edit Record: %s' % request,
            'formset' : formset,
            'read_only' : READ_ONLY,
            'error' : warning_msg,
            }) )

def process_formset(formset,request):
    ''' ingest the new or edit form and pass changes to the SPARQL endpoint query as a dictionary'''
    #for now, assume that the link has not changed, thus mapping record updates only allowed
    globalDateTime = datetime.datetime.now().isoformat()
    for form in formset:
        form_data=form.cleaned_data
        mapping_p_o = {}
        #take the new values from the form and add all of the initial values not included in the 'remove' field
        for label in ['owner','watcher']:
            mapping_p_o['%s' % label] = []
            if form.cleaned_data['add_%ss' % label] != '':
                for val in form.cleaned_data['add_%ss' % label].split(','):
                    mapping_p_o['%s' % label].append('"%s"' % val)
            if form.cleaned_data['%ss' % label] != 'None':
                for val in form.cleaned_data['%ss' % label].split(','):
                    if val not in form.cleaned_data['remove_%ss' % label].split(',') and\
                        val not in mapping_p_o['%s' % label].split(','):
                        mapping_p_o['%s' % label].append('"%s"' % val)
            if len(mapping_p_o['%s' % label]) == 0:
                mapping_p_o['%s' % label] = ['"None"']
                
        mapping_p_o['creator'] = ['"%s"' % form.cleaned_data['editor']]
        if mapping_p_o['creator'] == ['""']:
            mapping_p_o['creator'] = ['"None"']
        mapping_p_o['creation'] = ['"%s"^^xsd:dateTime' % globalDateTime]
        mapping_p_o['status'] = ['"%s"' % form.cleaned_data['next_status']]
        mapping_p_o['previous'] = ['<%s>' % form.cleaned_data['mapping']]
        mapping_p_o['comment'] = ['"%s"' % form.cleaned_data.get('comment')]
        if mapping_p_o['comment'] == ['""']:
            mapping_p_o['comment'] = ['"None"']
        mapping_p_o['reason'] = ['"%s"' % form.cleaned_data['reason']]
        mapping_p_o['linkage'] = ['<%s>' % form.cleaned_data['linkage']]

        #check to see if the updated mapping record is simply the last one
        if mapping_p_o['owner'] == ['"%s"' % form.cleaned_data['owners']] and \
        mapping_p_o['watcher'] == ['"%s"' % form.cleaned_data['watchers']] and \
        mapping_p_o['creator'] == ['"%s"' % form.cleaned_data['last_editor']] and \
        mapping_p_o['status'] == ['"%s"' % form.cleaned_data['current_status']] and \
        mapping_p_o['comment'] == ['"%s"' % form.cleaned_data.get('last_comment')] and \
        mapping_p_o['reason'] == ['"%s"' % form.cleaned_data['reason']] and \
        mapping_p_o['linkage'] == ['<%s>' % form.cleaned_data['linkage']]:
            changed = False
        else:
            changed = True
            

        if changed:
            res = moq.create_mapping(mapping_p_o)
                                  


         

def old_process_formset(formset, record):
    '''ingest the form, 'new' or 'edit': if altered and push changes to the tdb via SPARQL queries'''
    pre = prefixes.Prefixes()

    globalDateTime = datetime.datetime.now().isoformat()
    for form in formset:
        data = form.cleaned_data

        # mmd5 = hashlib.md5()
        # origin = record
        # mmd5.update(origin)
        # mmd5.update(data.get('unit'))
        # mmd5.update(data.get('standard_name'))

        provMD5 = hashlib.md5()
        linkage = '%s%s' % (pre.link, str(mmd5.hexdigest()))
        provMD5.update(data.get('owner', 'None'))
        provMD5.update(data.get('watcher', 'None'))
        provMD5.update(data.get('editor', 'None'))
        provMD5.update(data.get('next_status'))
        hasPrevious = '%s%s' % (pre.map, data.get('provenanceMD5')) 
        provMD5.update(hasPrevious)
        provMD5.update(data.get('comment'))
        provMD5.update(data.get('reason'))
        provMD5.update(linkage)

        if len(get_link(linkage)):
            #only run the insert if this is truely a new record
            insertDataStr = '''
                <%s> a iso19135:RegisterItem ;
                    metExtra:origin <%s> ;
                    cf:units "%s" ;
                    cf:name <%s> ;
                    metExtra:saveCache "True" .
            ''' % (
                linkage,
                origin,
                data.get('unit'),
                data.get('standard_name')
            )
        else:
            insertDataStr = ''
        #define the attributes of the mapping record    
        mapAttrs = {
            'owner':data.get('owner', 'None'),
            'watcher':data.get('watcher', 'None'),
            'editor':data.get('editor', 'None'),
            'status':data.get('next_status'),
            'comment':data.get('comment'),
            'reason':data.get('reason'),
            'linkage':linkage
            }



        if get_map_by_attrs(mapAttrs):
            #only run the insert if this is truely a new record            
            insertProvStr = '''
                <%s> a iso19135:RegisterItem ;
                    metExtra:hasOwner     "%s" ;
                    metExtra:hasWatcher   "%s" ;
                    metExtra:hasEditor    "%s" ;
                    metExtra:hasStatus    "%s" ;
                    metExtra:hasPrevious  <%s> ;
                    metExtra:hasLastEdit  "%s" ;
                    metExtra:hasComment   "%s" ;
                    metExtra:hasReason    "%s" ;
                    metExtra:link         <%s> ;
                    metExtra:saveCache "True" .
            ''' % (
                '%s%s' % (pre.map, str(provMD5.hexdigest())),
                mapAttrs['owner'],
                mapAttrs['watcher'],
                mapAttrs['editor'],
                mapAttrs['status'],
                hasPrevious,
                datetime.datetime.now().isoformat(), # hasLastEdit updated with current time
                mapAttrs['comment'],
                mapAttrs['reason'],
                mapAttrs['linkage']

            )
        else:
            insertProvStr = ''


        qstr = '''
        INSERT DATA {
            %s
            %s
        }
        ''' % (insertDataStr, insertProvStr)


        results = query.run_query(qstr, update=True)
        

def get_record(record, datatype):
    '''This returns the mapping and linkage records from the default graph in the triple-store using the format specific 'origin' as the search key.
    mappings are only returned if they are th elast entry in a hasPrevious chain and their status is not 'Deprecated' or 'Broken'
    '''
    
    qstr = '''
    SELECT DISTINCT ?prov ?previous ?cfname ?unit ?canon_unit ?last_edit ?long_name ?comment ?reason ?status ?link
    WHERE
    {

        ?link metExtra:origin <%s> ;
              metExtra:long_name ?long_name ;
              cf:units ?unit ;
              cf:name ?cfname .
        ?prov metExtra:link ?link .
        ?prov metExtra:hasPrevious ?previous ;
                metExtra:hasLastEdit ?last_edit ;
                metExtra:hasComment ?comment ;
                metExtra:hasStatus ?status ;
                metExtra:hasReason ?reason .
        OPTIONAL {

            ?cfname cf:canonical_units ?canon_unit .
        }
        FILTER (?status NOT IN ("Deprecated", "Broken")) .

        {
          SELECT ?prov ?previous
          WHERE
          {

           ?prov metExtra:hasPrevious ?previous . 
           MINUS {?prov ^metExtra:hasPrevious+ ?prov}
         
          }  
        }
    } 
    ''' % (record,)
    results = query.run_query(qstr)
    return results

def records(request):
    # report in column view
    pass


def record_bulk_load(request):
    # CSV file upload and report in column view for validation
    pass

# def get_counts_by_graph(graphurl=''):
#     '''This query relies on a feature of Jena that is not yet in the official
#     SPARQL v1.1 standard insofar as 'GRAPH ?g' has undetermined behaviour
#     under the standard but Jena interprets and treats the '?g' 
#     just like any other variable.
#     '''
    
#     qstr = '''
#         SELECT ?g (COUNT(DISTINCT ?s) as ?count)
#         WHERE {
#             GRAPH ?g { ?s ?p ?o } .
#             FILTER( REGEX(str(?g), '%s') ) .
#         }
#         GROUP by ?g
#         ORDER by ?g
#     ''' % graphurl
#     results = query.run_query(qstr)
#     return results

def get_link(linkID):
    '''returns a link record for the given link ID
    This is used to guard against creating multiple identical link records'''
    qstr = '''
    SELECT ?s ?p ?o
    WHERE
    {
    ?s ?p ?o.
    FILTER (?s = <%s>)
    }
    ''' % linkID
    results = query.run_query(qstr)
    return results

def get_map_by_attrs(mapAttrs):
    '''returns a mapping record using the subset of the mapping's attributes which define its nature
    This is used to guard against creating multiple identical mapping records
    '''
    qstr = '''
    SELECT ?s ?p ?o
    WHERE
    {
    ?s ?p ?o;
        metExtra:hasOwner     "%s" ;
        metExtra:hasWatcher   "%s" ;
        metExtra:hasEditor    "%s" ;
        metExtra:hasStatus    "%s" ;
        metExtra:hasComment   "%s" ;
        metExtra:hasReason    "%s" ;
        metExtra:link         <%s> ;    
    }
    ''' % (
        mapAttrs['owner'],
        mapAttrs['watcher'],
        mapAttrs['editor'],
        mapAttrs['status'],
        mapAttrs['comment'],
        mapAttrs['reason'],
        mapAttrs['linkage']
        )
    results = query.run_query(qstr)
    return results


def search(request):
    pass

def mapdisplay(request, hashval):
    '''Direct access to a Mapping record.
    Returns RDF but requires the correct mimetype to be set.
    '''
    
    pre = prefixes.Prefixes()
    qstr = '''
    CONSTRUCT 
    {
        <%s%s> metExtra:hasPrevious ?previous ;
                metExtra:hasOwner ?owner ;
                metExtra:hasWatcher ?watcher ;
                metExtra:hasEditor ?editor ;
                metExtra:hasStatus ?status ;
                metExtra:hasComment ?comment ;
                metExtra:hasReason ?reason ;
                metExtra:hasLastEdit ?last_edit ;
                metExtra:link ?linkage .
        ?linkage metExtra:origin ?vers ;
                metExtra:long_name ?long_name ;
                cf:units ?cfunits ;
                cf:name ?cfname . 
    }
    WHERE
    {   
        <%s%s> metExtra:hasPrevious ?previous ;
                metExtra:hasOwner ?owner ;
                metExtra:hasWatcher ?watcher ;
                metExtra:hasEditor ?editor ;
                metExtra:hasStatus ?status ;
                metExtra:hasComment ?comment ;
                metExtra:hasReason ?reason ;
                metExtra:hasLastEdit ?last_edit ;
                metExtra:link ?linkage .
        ?linkage metExtra:origin ?vers ;
                metExtra:long_name ?long_name ;
                cf:units ?cfunits ;
                cf:name ?cfname .
    } 
    ''' % (pre.map, hashval, pre.map, hashval)
    
    results = query.run_query(qstr, output='xml')
    return HttpResponse(results, mimetype='text/xml')


