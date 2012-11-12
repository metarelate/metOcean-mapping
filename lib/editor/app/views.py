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
import fusekiQuery as query
import metocean.prefixes as prefixes
import metocean.queries as moq
from settings import READ_ONLY






def home(request):
    searchurl = url_with_querystring(reverse('mapping'),ref='')
    search = {'url':searchurl, 'label':'search for a mapping'}
    context = RequestContext(request, {'search':search})
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

def format_param(request, format):
    '''
    '''
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    param_list = request_search_path.split('|')
    if format == 'um':
        Searchform = forms.UMParam
    elif format == 'cf':
        Searchform = forms.CFParam
    else:
        raise NameError("there is no form available for this format type")
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


def search(request):
    '''
    '''
    itemlist = ['Search Parameters:']
    umitems = []
    cfitems = []
    gribitems = []
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    param_list = request_search_path.split('|')
    for param in param_list:
        #itemlist.append(param)
        params = param.split(';')
        if params[0] == 'um':
            umitems.append(params[1])
        elif params[0] == 'cf':
            cfitems.append(params[1])
        elif params[0] == 'grib':
            gribitems.append(params[1])
    addumurl = url_with_querystring(reverse('format_param', kwargs={'format':'um'}),ref=request_search_path)
    addum = {'url':addumurl, 'label':'add UM parameter'}
    addcfurl = url_with_querystring(reverse('format_param', kwargs={'format':'cf'}),ref=request_search_path)
    addcf = {'url':addcfurl, 'label':'add CF parameter'}
    addgriburl = url_with_querystring(reverse('format_param', kwargs={'format':'grib'}),ref=request_search_path)
    addgrib = {'url':addgriburl, 'label':'add GRIB parameter'}
    searchurl = url_with_querystring(reverse('mapping'),ref=request_search_path)
    search = {'url':searchurl, 'label':'search'}
    clear = {'url':reverse('search'), 'label': 'clear'}
    context = RequestContext(request, {
        'itemlist' : itemlist,
        'umitems': umitems,
        'addum': addum,
        'cfitems': cfitems,
        'addcf': addcf,
        'gribitems': gribitems,
        'addgrib':addgrib,
        'search': search,
        'clear': clear,
        })
    return render_to_response('main.html', context)

# def search(request):
#     '''
#     '''
#     request_search_path = request.GET.get('ref', '')
#     request_search_path = urllib.unquote(request_search_path).decode('utf8')
#     param_list = request_search_path.split('|')
#     SearchFormset = formset_factory(forms.SearchParam, extra=0)
#     if request.method == 'POST':
#         print request.POST
#         formset = SearchFormset(request.POST)
#         if formset.is_valid():
#             parameters = []
#             for form in formset:
#                 parameters.append(form.cleaned_data['parameter'])
#                 param_string = '|'.join(parameters)
#             url = url_with_querystring(reverse('showsearchparams'),ref=param_string)
#             return HttpResponseRedirect(url)
#     else:
#         initial_dataset = []
#         for param in param_list:
#             dataset = {'parameter':param}
#             initial_dataset.append(dataset)
#         formset = SearchFormset(initial=initial_dataset)
#     context = RequestContext(request, {
#         'formset':formset,
#         })
#     return render_to_response('form.html', context)

def mapping(request):
    '''form view to edit one or more records, retrieved based on a format specific request'''
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = request_search_path.split('|')
    search_path = [(param.split(';')[0],param.split(';')[1]) for param in request_search]
    print search_path
    pre = prefixes.Prefixes()

    MappingFormSet = formset_factory(forms.MappingEditForm, extra=0)
    warning_msg = ''
    if request.method == 'POST':
        formset = MappingFormSet(request.POST)
        if formset.is_valid():
            process_formset(formset, request)
            return HttpResponseRedirect(url_with_querystring(reverse('mapping', ref=request_search_path)))
        else:
            print formset.errors
    else:
        urecordm = moq.mapping_by_link(search_path)
        if len(urecordm) > 1:
            warning_msg = (
                'Warning: '
                '%s Active Data Records with the same search pattern found.' %
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
    return render_to_response('form.html',
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
        mapping_p_o = collections.defaultdict(list)
        #take the new values from the form and add all of the initial values not included in the 'remove' field
        for label in ['owner','watcher']:
            if form.cleaned_data['add_()s'.format(label)] != '':
            #if form.cleaned_data['add_%ss' % label] != '':
                for val in form.cleaned_data['add_%ss' % label].split(','):
                    mapping_p_o[label].append('"%s"' % val)
            if form.cleaned_data['%ss' % label] != 'None':
                for val in form.cleaned_data['%ss' % label].split(','):
                    if val not in form.cleaned_data['remove_%ss' % label].split(',') and\
                        val not in mapping_p_o['%s' % label].split(','):
                        mapping_p_o[label].append('"%s"' % val)
            if len(mapping_p_o[label]) == 0:
                mapping_p_o[label] = ['"None"']
                
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
                                  
