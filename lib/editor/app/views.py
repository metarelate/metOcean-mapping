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

import collections
import datetime
import hashlib
import itertools
import os
import re
import sys
import urllib

from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.utils.safestring import mark_safe
from django.forms.formsets import formset_factory
from django.forms.models import inlineformset_factory


import forms
import metocean.prefixes as prefixes
import metocean.queries as moq
from settings import READ_ONLY
from settings import fuseki_process

def home(request):
    persist = fuseki_process.query_cache()
    cache_status = '%i statements in the local triple store are flagged as not existing in the persistent StaticData store' % len(persist)
    cache_state = moq.print_records(persist)
    if request.method == 'POST':
        form = forms.HomeForm(request.POST)
        if form.is_valid():
            pass
    else:
        form = forms.HomeForm(initial={'cache_status':cache_status, 'cache_state':cache_state})
    con_dict = {}
    searchurl = url_with_querystring(reverse('fsearch'),ref='')
    con_dict['search'] = {'url':searchurl, 'label':'search for mappings'}
    con_dict['control'] = {'control':'control'}
    con_dict['form'] = form
    context = RequestContext(request, con_dict)
    return render_to_response('main.html', context)


def url_with_querystring(path, **kwargs):
    ''' helper function '''
    return path + '?' + urllib.urlencode(kwargs)


def search_param(request):
    '''
    '''
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    param_list = request_search_path.split('|')
    Searchform = forms.SearchParam
    if request.method == 'POST': # If the form has been submitted...
        form = Searchform(request.POST) # A form bound to the POST data
        if form.is_valid():
            param_list.append(form.cleaned_data['parameter'])
            param_string = '|'.join(param_list).lstrip('|')
            url = url_with_querystring(reverse('search'),ref=param_string)
            return HttpResponseRedirect(url)
    else:
        form = Searchform()

    context = RequestContext(request, {
        'form':form,
        })
    return render_to_response('form.html', context)

def format_param(request, fformat):
    '''
    '''
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    param_list = request_search_path.split('|')
    if fformat == 'umSTASH':
        Searchform = forms.UMSTASHParam
    elif fformat == 'umFC':
        Searchform = forms.UMFCParam
    elif fformat == 'cf':
        Searchform = forms.CFParam
    elif fformat == 'grib':
        Searchform = forms.GRIBParam
    else:
        raise NameError("there is no form available for this format type")
    if request.method == 'POST': # If the form has been submitted...
        form = Searchform(request.POST) # A form bound to the POST data
        if form.is_valid():
            param_list.append(form.cleaned_data['parameter'])
            param_string = '|'.join(param_list).lstrip('|')
            if fformat.startswith('um'):
                fformat = 'um'
            url = url_with_querystring(reverse('search', kwargs={'fformat':fformat}), ref=param_string)
            return HttpResponseRedirect(url)
    else:
        form = Searchform()

    context = RequestContext(request, {
        'form':form,
        })
    return render_to_response('form.html', context)


def fsearch(request):
    """
    Select a format
    """
    urls = {}
    formats = ['um', 'cf', 'grib']
    for form in formats:
        searchurl = url_with_querystring(reverse('search', kwargs={'fformat':form}),ref='')
        search = {'url':searchurl, 'label':'search for %s concepts' % form}
        urls[form] = search
    context = RequestContext(request, urls)
    return render_to_response('main.html', context)
        
    

def search(request, fformat):
    """Select a set of parameters for a concept search"""
    itemlist = ['Search Parameters:']
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    paramlist = request_search_path.split('|')
    for param in paramlist:
        itemlist.append(param)
    con_dict = {'itemlist' : itemlist}
    if fformat == 'um':
        stashurl = url_with_querystring(reverse('format_param', kwargs={'fformat':fformat + 'STASH'}),ref=request_search_path)
        addstash = {'url':stashurl, 'label': 'add STASH concept'}
        con_dict['addstash'] = addstash
        fcurl = url_with_querystring(reverse('format_param', kwargs={'fformat':fformat + 'FC'}),ref=request_search_path)
        addfc = {'url':fcurl, 'label': 'add Field Code'}
        con_dict['addfc'] = addfc
    else:
        addurl = url_with_querystring(reverse('format_param', kwargs={'fformat':fformat}),ref=request_search_path)
        add = {'url':addurl, 'label':'add parameter'}
        con_dict['add'] = add
    conurl = url_with_querystring(reverse('concepts', kwargs={'fformat':fformat}), ref=request_search_path)
    concepts = {'url':conurl, 'label':'find partially matching concepts'}
    xconurl = url_with_querystring(reverse('concept', kwargs={'fformat':fformat}), ref=request_search_path)
    xconcepts = {'url':xconurl, 'label':'find exactly matching concepts'}
    con_dict['search'] = concepts
    con_dict['exact'] = xconcepts
    clearurl = url_with_querystring(reverse('search', kwargs={'fformat':fformat}), ref='')
    con_dict['clear'] = {'url':clearurl, 'label':'clear parameters'}
    context = RequestContext(request,con_dict)
    return render_to_response('main.html', context)

def concept(request, fformat):
    """
    returns a view of the concept exactly matching the search pattern
    """
    if fformat == 'grib':
        fformat = 'grib/2'
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    search_path = request_search_path.split('|')
    components = ['<%s>' % component for component in search_path]
    po_dict = {'mr:format':'<http://metarelate.net/metocean/format/%s>' % fformat,
                'mr:component':components}
    context_dict = {}
    if request.method == 'POST':
        form = forms.ConceptForm(request.POST)
        if form.is_valid():
            #redirect
            if form.cleaned_data['operation'] == 'create':
                concept_match = moq.get_concept(fuseki_process, po_dict, create=True)
            redirect = url_with_querystring(reverse('mappings'), ref=request_search_path)
            return HttpResponseRedirect(redirect)
        else:
            print form.errors
            
    else:        
        concept_match = moq.get_concept(fuseki_process, po_dict, create=False)
        con_strs = moq.concept_components(fuseki_process, concept_match)
        if len(con_strs) == 1:
            con = con_strs[0]
            concept = con['concept']
            components = con['components'].split('&')
            component_view = [component.split('/')[-1] for component in components]
            init = {'concept':concept, 'components': '&'.join(component_view), 'display': True}
            form = forms.ConceptForm(initial = init)
            
        elif len(con_strs) == 0:
            context_dict['create'] = True
            component_view = [component.split('/')[-1] for component in search_path]
            init = {'components': '&'.join(component_view), 'display': True}
            form = forms.ConceptForm(initial = init)
        else:
            raise ValueError('Two exact matches for concept exist: %s' % search_path) 
    
    context_dict['form'] = form
    context_dict['read_only'] =  READ_ONLY
            
    context = RequestContext(request, context_dict)
    return render_to_response('form.html', context)
        

def concepts(request, fformat):
    """returns a view listing all the concepts which match or submatch the search pattern
    """
    if fformat == 'grib':
        fformat = 'grib/2'
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = request_search_path.split('|')
    if request_search != [u'']:
        search_path = request_search
    else:
        search_path = False#[('','')]
    ConceptFormSet = formset_factory(forms.ConceptForm, extra=0)
    if request.method == 'POST': # If the form has been submitted...
        formlist = ConceptFormSet(data=request.POST)
        concepts = []
        if formlist.is_valid():
            for form in formlist:
                if form.cleaned_data['display'] is True:
                    concepts.append(form.cleaned_data['concept'])
            param_string = '|'.join(concepts)
            url = url_with_querystring(reverse('mappings'),ref=param_string)
            return HttpResponseRedirect(url)
        else:
            print formlist.errors
    else:
        if search_path:
            components = ['<%s>' % component for component in search_path]
            po_dict = {'mr:format':'<http://metarelate.net/metocean/format/%s>' % fformat,
                   'mr:component':components}
        else:
            po_dict = {'mr:format':'<http://metarelate.net/metocean/format/%s>' % fformat}
        concept_match = moq.get_superset_concept(fuseki_process, po_dict)
        initial_dataset = []
        con_strs = moq.concept_components(fuseki_process, concept_match)
        for con in con_strs:
            concept = con['concept']
            components = con['components'].split('&')
            component_view = [component.split('/')[-1] for component in components]
            init = {'concept':concept, 'components': '&'.join(component_view), 'display': True}
            initial_dataset.append(init)
        formlist = ConceptFormSet(initial = initial_dataset)
    context_dict = {

        'formlist' : formlist,
        'read_only' : READ_ONLY,
        }
    context = RequestContext(request, context_dict)
    return render_to_response('form.html', context)

def mappings(request):
    """
    list mappings which reference the concept search criteria
    by concept by source then target
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = request_search_path.split('|')
    if request_search != [u'']:
        search_path = request_search
    else:
        search_path = False#[('','')]
    MappingFormSet = formset_factory(forms.MappingForm, extra=0)
    if request.method == 'POST': # If the form has been submitted...
        formlist = MappingFormSet(data=request.POST)
        mappings = []
        if formlist.is_valid():
            for form in formlist:
                if form.cleaned_data['display'] is True:
                    mappings.append(form.cleaned_data['mapping'])
            param_string = '|'.join(mappings)
            url = url_with_querystring(reverse('edit_mappings'),ref=param_string)
            return HttpResponseRedirect(url)
        else:
            print formlist.errors
    else:
        #print 'request.GET: ', request.GET
        #print 'request: ', request
        initial_dataset = []
        if search_path:
            concepts = ['<%s>' % source for source in search_path]
            mappings = moq.mappings_by_concept(fuseki_process, concepts)
        else:
            mappings = []
        for mapping in mappings:
            source_strs = moq.concept_components(fuseki_process, [{'concept': mapping['source']}])
            target_strs = moq.concept_components(fuseki_process,[{'concept': mapping['target']}])
            if len(source_strs) != 1 or len(target_strs) != 1:
                raise ValueError('one and only one source list and target list is required, but not delivered')
            sources = source_strs[0]['components'].split('&')
            if source_strs[0].has_key('cfitems'):
                source_view = [','.join([ss.split(';')[1].split('/')[-1] for ss in source_strs[0]['cfitems'].split('&')])]
            else:
                source_view = [source.split('/')[-1] for source in sources]
            targets = target_strs[0]['components'].split('&')
            if target_strs[0].has_key('cfitems'):
                target_view = [','.join([ts.split(';')[1].split('/')[-1] for ts in target_strs[0]['cfitems'].split('&')])]
            else:
                target_view = [target.split('/')[-1] for target in targets]
            init = {'mapping':mapping['map'], 'source': '&'.join(source_view), 'target': '&'.join(target_view), 'display': True}
            initial_dataset.append(init)
        formlist = MappingFormSet(initial = initial_dataset)
    context_dict = {
        'formlist' : formlist,
        'read_only' : READ_ONLY,
        }
    if len(request_search) == 1:
        create_url = url_with_querystring(reverse('new_mapping'), ref=request_search_path)
        create = {'url':create_url, 'label':'create a new mapping'}
        context_dict['create'] = create
    context = RequestContext(request, context_dict)
    return render_to_response('form.html', context)

    


def new_mapping(request):
    '''form view to create a new mapping record'''
    ## need to implement the functinoality to
      ##select the other concept
      ## reverse direction
      ## make a pair of mirror mappings
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = request_search_path.split('|')
    # dataset = None
    # if request_search != [u'']:
    #     fso_dict = collections.defaultdict(list)
    #     print 'searching'
    #     search_path = [(param.split(';')[0],param.split(';')[1]) for param in request_search]
    #     for elem in search_path:
    #         fso_dict['mr:%slink' % (elem[0].upper())].append('<%s>' % elem[1])
    #     #linkage = moq.get_linkage(fuseki_process, fso_dict)
    #     #print 'linkage: ', linkage
    #     #should only have 1 res > imposed by queries
    #     #dataset = linkage[0]
    #     dataset = {'mapping': ""}
    #     #dataset[
    # else:
    #     print 'not searching'
    #     #redirect to search
    #     #search_path = [('','')]
    MapForm = forms.MappingNewForm
    if request.method == 'POST': # If the form has been submitted...
        form = MapForm(request.POST) # A form bound to the POST data
        if form.is_valid():
            print form.cleaned_data
            process_form(form, request)
            url = url_with_querystring(reverse('mapping'),ref=request_search_path)
            return HttpResponseRedirect(url)
    else:
        if dataset:
            form = MapForm(initial=dataset)
        else:
            form = MapForm()

    context = RequestContext(request, {
        'form':form,
        })
    return render_to_response('form.html', context)

    

def edit_mappings(request):
    '''form view to edit one or more records, retrieved based on a format specific request'''
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = request_search_path.split('|')
    if request_search != [u'']:
        search_path = request_search
        #print search_path
    else:
        search_path = False#[('','')]
    pre = prefixes.Prefixes()

    MappingFormSet = formset_factory(forms.MappingEditForm, extra=0)
    warning_msg = ''
    if request.method == 'POST':
        formset = MappingFormSet(request.POST)
        if formset.is_valid():
            # process formset creates a new mapping record for
            # each form which has changed and returns the list of
            # mapping IDs for created and unchanged mappings
            
            query_search_path = process_formset(formset, request)
            return HttpResponseRedirect(url_with_querystring(
                reverse('edit_mappings'), ref=query_search_path))
        else:
            print formset.errors
    else:
        map_records = moq.mapping_by_id(fuseki_process, search_path)
        initial_data_set = []
        if len(map_records) > 0:
            for item in map_records:
                data_set = {}
                mapurl = item.get('map')
                source = item.get('source')
                if item.get('source_cfitems') is not None:
                    #source = item.get('relates_cfitems')
                    source_view = ''
                    cftargets = item.get('source_cfitems').split('&')
                    for cft in cftargets:
                        source_view = '|'.join([','.join([ss.split(';')[1].split('/')[-1]
                                                      for ss in item.get('source_cfitems').split('|')])])
                else:
                    source_view = '&'.join([s.split('/')[-1] for s in item.get('source_comps').split('&')])
                target = item.get('target')
                if item.get('target_cfitems') is not None:
                    #target = item.get('target_cfitems')
                    cftargets = item.get('target_cfitems').split('&')
                    target_view = ''
                    for cft in cftargets:
                        target_view += '|'.join([','.join([ss.split(';')[1].split('/')[-1]
                                                          for ss in cft.split('|')])])
                else:
                    target_view = '&'.join([t.split('/')[-1] for t in item.get('target_comps').split('&')])
                data_set = dict(
                    mapping = item.get('map'),
                    last_edit = item.get('creation'),
                    last_editor = item.get('creator'),
                    current_status = item.get('status'),
                    last_comment = item.get('comment'),
                    last_reason = item.get('reason'),
                    owners = item.get('owners'),
                    watchers = item.get('watchers'),
                    replaces = item.get('replaces'),
                    #replaces = mark_safe("%s" % replaceslabel),
                    #replaces = replacesurl,
                    sources = source,
                    sources_view = source_view,
                    targets = target,
                    targets_view = target_view,
                    )
                initial_data_set.append(data_set)
        formset = MappingFormSet(initial=initial_data_set)
    context_dict = {'viewname' : 'Edit Record',
            'title' : 'Edit Record: %s' % request,
            'formset' : formset,
            'read_only' : READ_ONLY,
            'error' : warning_msg,}
    context = RequestContext(request, context_dict)
    return render_to_response('form.html', context)
        

def process_formset(formset,request):
    ''' ingest the new or edit form and pass changes to the SPARQL endpoint query as a dictionary'''
    #for now, assume that the link has not changed, thus mapping record updates only allowed
    maps = []
    for form in formset:
        maps.append(process_form(form, request))
    mappings = '|'.join(maps)
    return mappings

def process_form(form, request):
    globalDateTime = datetime.datetime.now().isoformat()
    form_data=form.cleaned_data
    mapping_p_o = collections.defaultdict(list)
    #take the new values from the form and add all of the initial values not included in the 'remove' field
    for label in ['owner','watcher']:
        #if form.cleaned_data['add_()s'.format(label)] != '':
        if form.cleaned_data['add_%ss' % label] != '':
            for val in form.cleaned_data['add_%ss' % label].split(','):
                mapping_p_o['mr:%s' % label].append('"%s"' % val)
        if form.cleaned_data['%ss' % label] != '':
            for val in form.cleaned_data['%ss' % label].split(','):
                if val not in form.cleaned_data['remove_%ss' % label].split(',') and\
                    val not in mapping_p_o['mr:%s' % label].split(','):
                    mapping_p_o['mr:%s' % label].append('"%s"' % val)
        #if len(mapping_p_o['mr:%s' % label]) == 0:
        #    mapping_p_o['mr:%s' % label] = ['"None"']

    mapping_p_o['mr:creator'] = ['<%s>' % form.cleaned_data['editor']]
    if mapping_p_o['mr:creator'] == ['""']:
        mapping_p_o['mr:creator'] = ['"None"']
    mapping_p_o['mr:creation'] = ['"%s"^^xsd:dateTime' % globalDateTime]
    mapping_p_o['mr:status'] = ['"%s"' % form.cleaned_data['next_status']]
    if form.cleaned_data['mapping'] != "":
        mapping_p_o['dc:replaces'] = ['<%s>' % form.cleaned_data['mapping']]
    if form.cleaned_data['comment'] != '':
        mapping_p_o['mr:comment'] = ['"%s"' % form.cleaned_data['comment']]
    mapping_p_o['mr:reason'] = ['"%s"' % form.cleaned_data['reason']]
    mapping_p_o['mr:relates'] = ['<%s>' % relates for relates in form.cleaned_data['sources'].split('&')]
    mapping_p_o['mr:target'] = ['<%s>' % target for target in form.cleaned_data['targets'].split('&')]

    #check to see if the updated mapping record is simply the last one
    changed = False
    if mapping_p_o.has_key('mr:owner') and \
        mapping_p_o['mr:owner'] != ['"%s"' % owner for owner in form.cleaned_data['owners'].split(',')]:
        changed = True
        print 'owner: changed = True'
    if mapping_p_o.has_key('mr:watcher') and \
        mapping_p_o['mr:watcher'] != ['"%s"' % watcher for watcher in form.cleaned_data['watchers'].split(',')]:
        changed = True
        print 'watcher: changed = True'
    if mapping_p_o['mr:creator'] != ['"%s"' % form.cleaned_data['last_editor']]:
        changed = True
        print 'creator: changed = True'
    if mapping_p_o['mr:status'] != ['"%s"' % form.cleaned_data['current_status']]:
        changed = True
        print 'status: changed = True'
    if mapping_p_o.has_key('mr:comment') and \
        mapping_p_o['mr:comment'] != ['"%s"' % form.cleaned_data['comment']]:
        changed = True
        print 'comment: changed = True'
    if mapping_p_o['mr:reason'] != ['"%s"' % form.cleaned_data['reason']]:
        changed = True
        print 'reason: changed = True'
    if mapping_p_o['mr:relates'] != ['"%s"' % form.cleaned_data['sources']]:
        changed = True
        print 'relates: changed = True'
    if mapping_p_o['mr:target'] != ['"%s"' % form.cleaned_data['targets']]:
        changed = True
        print 'target: changed = True'


    print 'changed: ', changed
    print mapping_p_o

    if changed:
        mapping = moq.create_mapping(fuseki_process, mapping_p_o, True)
    else:
        mapping = form.cleaned_data['mapping']
        print 'unchanged'

    return mapping

