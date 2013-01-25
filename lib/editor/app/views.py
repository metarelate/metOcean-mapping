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
import copy
import datetime
import hashlib
import itertools
import json
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
            invalids = form.cleaned_data.get('validation')
            if invalids:
                for key in invalids:
                    invalids[key] = '|'.join([inv['amap'] for inv in invalids[key]])
                #request_string = '&'.join(['%s;%sd' % (key, invalids[key])  for key in invalids[key]])
                request_string = '|'.join([invalids[key] for key in invalids])
                print request_string
                url = url_with_querystring(reverse('invalid_mappings'),ref=request_string)
                return HttpResponseRedirect(url)
            else:
                url = url_with_querystring(reverse('home'))
                return HttpResponseRedirect(url)
                
                
    else:
        form = forms.HomeForm(initial={'cache_status':cache_status, 'cache_state':cache_state})
    con_dict = {}
    searchurl = url_with_querystring(reverse('fsearch'),ref='')
    con_dict['search'] = {'url':searchurl, 'label':'search for mappings'}
    createurl = reverse('mapping_formats')
    con_dict['create'] = {'url':createurl, 'label':'create a new mapping'}
    con_dict['control'] = {'control':'control'}
    con_dict['form'] = form
    context = RequestContext(request, con_dict)
    return render_to_response('main.html', context)

def mapping_formats(request):
    """
    a view to define the formats for the mapping_concept
    """
    if request.method == 'POST':
        form = forms.MappingFormats(data=request.POST)
        if form.is_valid():
            referrer = {'mr:source':{'mr:format':form.cleaned_data['source_format'],
                                     'skos:member':[]},
                        'mr:target':{'mr:format':form.cleaned_data['target_format'],
                                     'skos:member':[]}}
            url = url_with_querystring(reverse('mapping_concepts'),ref=json.dumps(referrer))
            return HttpResponseRedirect(url)
    else:
        form = forms.MappingFormats()
    context = RequestContext(request, {'form':form})
    return render_to_response('simpleform.html', context)

def val_id(members):
    """helper"""
    value_list = []
    val_ids = []
    for mem in members:
        if mem.get('rdf:Property'):
            res = moq.get_value(fuseki_process, mem)
            vid = '<%s>' % res[0]['value']
            mem['id'] = '<%s>' % vid
            val_ids.append(vid)
    return val_ids

def mapping_concepts(request):
    """
    a view to present the mapping concepts, source and target, and the valuemaps and enable 
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request_search_path == '':
        request_search_path = '{}'
    request_search = json.loads(request_search_path)
    print 'request_search: ', request_search
    amended_dict = copy.deepcopy(request_search)
    if request.method == 'POST':
        ## get the formatConcepts for source and target
        ## pass to value map definition
        form = forms.MappingConcept(request.POST)
        concepts = {}
        new_map = copy.deepcopy(request_search)
        for key in ['mr:source','mr:target']:
            if isinstance(request_search[key]['skos:member'], list):
                subc_ids = []
                for i,member in enumerate(request_search[key]['skos:member']):
                    if member.get('skos:member') is not None:
                        val_ids = val_id(member.get('skos:member'))
                        sub_concept_dict = {'mr:format':'<%s>' % request_search[key]['mr:format'],
                                            'skos:member':val_ids}
                        sub_concept = moq.get_format_concept(fuseki_process, sub_concept_dict)
                        subc_ids.append('<%s>' % sub_concept[0]['formatConcept'])
                        new_map[key]['skos:member'][i]['id'] = '<%s>' % sub_concept[0]['formatConcept']
                val_ids = val_id(request_search[key]['skos:member'])
                concept_dict = {'mr:format':'<%s>' % request_search[key]['mr:format'],
                                            'skos:member':val_ids+subc_ids}
                concept = moq.get_format_concept(fuseki_process, concept_dict)
                if len(concept) == 1:
                    concepts[key] = concept[0]['formatConcept']
#        print 'concepts:', concepts
        if False:
            #find mappings, handle overlap, etc
            pass
        else:
            for key in ['mr:source','mr:target']:
                if concepts.has_key(key):
                    # new_map[key] = {concepts[key]:new_map[key]}
                    new_map[key]['id'] = '<%s>' % concepts[key]
                else:
                    raise ValueError('The source and target are not both defined')
            ref = json.dumps(new_map)
#            print ref
            url = url_with_querystring(reverse('value_maps'),ref=ref)
            return HttpResponseRedirect(url)
                    
                    
    else:
        form = forms.MappingConcept()
        for key in ['mr:source','mr:target']:
            if request_search[key].get('skos:member') is not None:
                if isinstance(request_search[key]['skos:member'], list):
                    ## a url to add a new sub_concept
                    fterm = copy.deepcopy(request_search)
                    fterm[key]['skos:member'].append({"skos:member":[]})
                    amended_dict[key]['skos:member'].append({'url':
                                                url_with_querystring(reverse('mapping_concepts'),
                                                           ref=json.dumps(fterm)), 'label':
                                                           'add a sub_concept'})
                    new_term = copy.deepcopy(request_search)
                    new_term[key]['skos:member'].append('&&&&')
                    amended_dict[key]['skos:member'].append({'url':url_with_querystring(
                        reverse('define_value', 
                                kwargs={'fformat':new_term[key]['mr:format'].split('/')[-1]}),
                                ref=json.dumps(new_term)), 'label':'add a value definition'})
                    for i, element in enumerate(request_search[key]['skos:member']):
                        remover = copy.deepcopy(request_search)
                        del remover[key]['skos:member'][i]
                        url = url_with_querystring(reverse('mapping_concepts'),
                                                           ref=json.dumps(remover))
                        amended_dict[key]['skos:member'][i]['remove'] = {'url':url,
                                                'label':'remove this item'}
                        if element.get('skos:member') is not None:
                            addition = copy.deepcopy(request_search)
                            addition[key]['skos:member'][i]["skos:member"].append('&&&&')
                            url = url_with_querystring(reverse('define_value',
                                kwargs={'fformat':addition[key]['mr:format'].split('/')[-1]}),
                                ref=json.dumps(addition))
                            amended_dict[key]['skos:member'][i]["skos:member"].append({'url':url, 'label':'add a value definition'})
                            for j, element in enumerate(request_search[key]['skos:member'][i]['skos:member']):
                                remover = copy.deepcopy(request_search)
                                del remover[key]['skos:member'][i]['skos:member'][j]
                                url = url_with_querystring(reverse('mapping_concepts'),
                                                                   ref=json.dumps(remover))
                                amended_dict[key]['skos:member'][i]['skos:member'][j]['remove'] = {'url':url,
                                                        'label':'remove this item'}                        
    con_dict = {}
    con_dict['mapping'] = amended_dict
    con_dict['form'] = form
    context = RequestContext(request, con_dict)
    return render_to_response('mapping_concept.html', context)

def value_maps(request):
    """
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request_search_path == '':
        request_search_path = '{}'
    request_search = json.loads(request_search_path)
    amended_dict = copy.deepcopy(request_search)
    if request.method == 'POST':
        ## create the valuemaps as defined
        ## check if a mapping (including invalid) provides this source to target
        #### or this source to a different target (same format)
        #### perhaps render this on a new screen
        ## then pass the json of {source:{},target:{},valueMaps[{}]
        ## to mapping_edit for creation
        form = forms.MappingConcept(request.POST)
        for valmap in request_search['mr:valueMap']:
            vmap = moq.get_value_map(fuseki_process, valmap)
            vmap_id = vmap[0]['valuemap']
            valmap['id'] = vmap_id
        url = url_with_querystring(reverse('mapping_edit'), ref = json.dumps(request_search))
        return HttpResponseRedirect(url)
            
    else:
        form = forms.MappingConcept()
        if not amended_dict.has_key('mr:valueMap'):
            addition = copy.deepcopy(request_search)
            addition['mr:valueMap'] = []
            url = url_with_querystring(reverse('define_valuemaps'), ref=json.dumps(addition))
            amended_dict['addValueMap'] = {'url':url, 'label':'add a value mapping'}
        else:
            url = url_with_querystring(reverse('define_valuemaps'), ref=json.dumps(request_search))
            amended_dict['addValueMap'] = {'url':url, 'label':'add a value mapping'}
            
    con_dict = {}
    con_dict['mapping'] = amended_dict
    con_dict['form'] = form
    context = RequestContext(request, con_dict)
    return render_to_response('mapping_concept.html', context)
    
def define_valuemap(request):
    """
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = json.loads(request_search_path)
    source_choices = []
    target_choices = []
    choices = [('mr:source', source_choices),('mr:target', target_choices)]
    for ch in choices:
        for elem in request_search[ch[0]]['skos:member']:
            if elem.has_key('rdf:Property'):
                ch[1].append(('%s||%s' % (request_search[ch[0]]['id'],
                                       elem['rdf:Property']),
                           elem['rdf:Property'].split('/')[-1]))
        for elem in request_search[ch[0]]['skos:member']:
            if elem.has_key('skos:member'):
                for selem in elem['skos:member']:
                    if selem.has_key('rdf:Property'):
                        ch[1].append(('%s||%s' % (elem['id'],
                                               selem['rdf:Property']),
                                   '  - %s' % selem['rdf:Property'].split('/')[-1]))

    if request.method == 'POST':
        form = forms.ValueMap(request.POST, sc=source_choices, tc=target_choices)
        if form.is_valid():
            source = form.cleaned_data['source_value'].split('||')
            target = form.cleaned_data['target_value'].split('||')
            request_search['mr:valueMap'].append({'mr:sourceFC':source[0],
                                                  'mr:sourceVal':source[1],
                                                  'mr:targetFC':target[0],
                                                  'mr:targetVal':target[1]})
            request_search_path = json.dumps(request_search)
            url = url_with_querystring(reverse('value_maps'),ref=request_search_path)
            return HttpResponseRedirect(url)
    else:
        form = forms.ValueMap(sc=source_choices, tc=target_choices)
    con_dict = {'form':form}
    context = RequestContext(request, con_dict)
    return render_to_response('simpleform.html', context)

def define_value(request, fformat):
    """
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request.method == 'POST':
        form = forms.Value(request.POST, fformat=fformat)
        if form.is_valid():
            new_value = {'rdf:Property' : form.cleaned_data['vproperty']}
            if form.cleaned_data['vliteral'] != '""':
                new_value['rdfs:literal'] =  form.cleaned_data['vliteral']
            newv = json.dumps(new_value)
            request_search_path = request_search_path.replace('"&&&&"', newv)
            url = url_with_querystring(reverse('mapping_concepts'),ref=request_search_path)
            return HttpResponseRedirect(url)
    else:
        form = forms.Value(fformat=fformat)
    con_dict = {'form':form}
    context = RequestContext(request, con_dict)
    return render_to_response('simpleform.html', context)


def define_concept(request, fformat):
    """
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request.method == 'POST':
        form = forms.FormatConcept(request.POST, fformat=fformat)
        if form.is_valid():
            new_value = {'skos:member':[{}]}
            newv = json.dumps(new_value)
            request_search_path = request_search_path.replace('"&&&&"', newv)
            url = url_with_querystring(reverse('mapping_concepts'),ref=request_search_path)
            return HttpResponseRedirect(url)
    else:
        form = forms.FormatConcept(fformat=fformat)
    con_dict = {'form':form}
    context = RequestContext(request, con_dict)
    return render_to_response('simpleform.html', context)

    
def mapping_edit(request):
    """
    a view to provide editing to the mapping record defining a
    source target and any valuemaps from the referrer
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request_search_path == '':
        request_search_path = '{}'
    request_search = json.loads(request_search_path)
    if request.method == 'POST':
        form = forms.MappingMeta(request.POST)
        if form.is_valid():
            map_id = process_form(form, request_search_path)
            request_search['id'] = map_id
            url = url_with_querystring(reverse('mapping_edit'),
                                       ref=json.dumps(request_search))
            return HttpResponseRedirect(url)
    else:
        ## look for mapping, if it exists, show it, with a warning
        ## if a partially matching mapping exists, handle this (somehow)
        initial = {'source':request_search.get('mr:source').get('id'),
                   'target':request_search.get('mr:target').get('id'),
                   'valueMaps':'&'.join([vm.get('id') for vm in request_search.get('mr:valueMap', [])])
            }
        map_id = request_search.get('id')
        if map_id:
            mapping = moq.get_mapping_by_id(fuseki_process, map_id)
            print mapping
            ts = initial['source'] == mapping['source']
            tt = initial['target'] == mapping['target']
            tvm = initial['valueMaps'].split('&').sort() == mapping['valueMaps'].split('&').sort()
            if ts and tt and tvm:
                initial = mapping                
            else:
                raise ValueError('mismatch in referrer')
            
            
        form = forms.MappingMeta(initial)
    con_dict = {}
    con_dict['mapping'] = request_search
    con_dict['form'] = form
    context = RequestContext(request, con_dict)
    return render_to_response('mapping_concept.html', context)



def process_form(form, request_search_path):
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

    mapping_p_o['dc:creator'] = ['<%s>' % form.cleaned_data['editor']]
    mapping_p_o['dc:date'] = ['"%s"^^xsd:dateTime' % globalDateTime]
    mapping_p_o['mr:status'] = ['"%s"' % form.cleaned_data['next_status']]
    if form.cleaned_data['mapping'] != "":
        mapping_p_o['dc:replaces'] = ['<%s>' % form.cleaned_data['mapping']]
    if form.cleaned_data['comment'] != '':
        mapping_p_o['skos:note'] = ['"%s"' % form.cleaned_data['comment']]
    mapping_p_o['mr:reason'] = ['"%s"' % form.cleaned_data['next_reason']]
    mapping_p_o['mr:source'] = ['%s' % form.cleaned_data['source']]
    mapping_p_o['mr:target'] = ['%s' % form.cleaned_data['target']]
    mapping_p_o['mr:invertible'] = ['"%s"' % form.cleaned_data['invertible']]
    mapping_p_o['mr:valueMap'] = ['<%s>' % vm for vm in form.cleaned_data['valueMaps'].split('&')]

    # #check to see if the updated mapping record is simply the last one
    # changed = False
    # if mapping_p_o.has_key('mr:owner') and \
    #     mapping_p_o['mr:owner'] != ['"%s"' % owner for owner in form.cleaned_data['owners'].split(',')]:
    #     changed = True
    #     print 'owner: changed = True'
    # if mapping_p_o.has_key('mr:watcher') and \
    #     mapping_p_o['mr:watcher'] != ['"%s"' % watcher for watcher in form.cleaned_data['watchers'].split(',')]:
    #     changed = True
    #     print 'watcher: changed = True'
    # if mapping_p_o['dc:creator'] != ['<%s>' % form.cleaned_data['last_editor']]:
    #     changed = True
    #     print 'creator: changed = True'
    # if mapping_p_o['mr:status'] != ['"%s"' % form.cleaned_data['current_status']]:
    #     changed = True
    #     print 'status: changed = True'
    # if mapping_p_o.has_key('skos:note') and \
    #     mapping_p_o['skos:note'] != ['"%s"' % form.cleaned_data['comment']]:
    #     changed = True
    #     print 'comment: changed = True'
    # if mapping_p_o['mr:reason'] != ['"%s"' % form.cleaned_data['reason']]:
    #     changed = True
    #     print 'reason: changed = True'
    # if mapping_p_o['mr:source'] != ['<%s>' % form.cleaned_data['source']]:
    #     changed = True
    #     print 'source: changed = True'
    # if mapping_p_o['mr:target'] != ['<%s>' % form.cleaned_data['target']]:
    #     changed = True
    #     print 'target: changed = True'
    # if mapping_p_o['mr:invertible'] != []:
    #     changed = True
    #     print 'invertible: changed = True'
    # if mapping_p_o['mr:valueMaps'] != ['<%s>' % form.cleaned_data['target']]:
    #     changed = True
    #     print 'target: changed = True'



#    print 'changed: ', changed
    print mapping_p_o

#    if changed:
    print 'create:', mapping_p_o
    mapping = mapping_p_o
    mapping = moq.create_mapping(fuseki_process, mapping_p_o)
    map_id = mapping[0]['map']
#    else:
#        mapping = form.cleaned_data['mapping']
#        print 'unchanged'
    # url = url_with_querystring(reverse('mapping_edit'), ref=request_search_path)
    # return HttpResponseRedirect(url)
    return map_id














#####legacy

# def cfitems_str(cfitems):
#     """returns the collection of cfitems as a single string,
#     removing all url encoding from the elements,
#     for viewing on screen"""
#     print 'cfitems: ', cfitems
#     items = cfitems.split('&')
#     items = [i.split('|') for i in items]
#     items = [[j.split(';')[0].split('#')[-1] +';' + j.split(';')[1].split('/')[-1] for j in i] for i in items]
#     cfi = '&'.join(['|'.join(elem) for elem in items])
#     return cfi


# def gribitems_str(gribitems):
#     """returns the collection of grib items as a single string,
#     removing all url encoding from the elements,
#     for viewing on screen
#     """
#     return None

# def fcitems_str(gribitems):
#     """returns the collection of fieldcode items as a single string,
#     removing all url encoding from the elements,
#     for viewing on screen
#     """
#     return None
    
# def stashitems_str(gribitems):
#     """returns the collection of stash items as a single string,
#     removing all url encoding from the elements,
#     for viewing on screen
#     """
#     return None

    


def invalid_mappings(request):
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
        initial_dataset = []
        if search_path:
            mappings = moq.mapping_by_id(fuseki_process, search_path)
        else:
            mappings = []
        for mapping in mappings:
            sources = mapping['source_comps'].split('&')
            targets = mapping['target_comps'].split('&')
            source_view = '&'.join([source.split('/')[-1] for source in sources])
            target_view = '&'.join([target.split('/')[-1] for target in targets])
            target_view = cfitems_str(mapping['target_cfitems'])
            init = {'mapping':mapping['map'], 'source': source_view, 'target': target_view, 'display': True}
            initial_dataset.append(init)
        formlist = MappingFormSet(initial = initial_dataset)
    context_dict = {
        'formlist' : formlist,
        'read_only' : READ_ONLY,
        }
    context = RequestContext(request, context_dict)
    return render_to_response('form.html', context)


    

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

# def mappings(request):
#     """
#     list mappings which reference the concept search criteria
#     by concept by source then target
#     """
#     request_search_path = request.GET.get('ref', '')
#     request_search_path = urllib.unquote(request_search_path).decode('utf8')
#     request_search = request_search_path.split('|')
#     if request_search != [u'']:
#         search_path = request_search
#     else:
#         search_path = False#[('','')]
#     print 'search_path: ', search_path
#     MappingFormSet = formset_factory(forms.MappingForm, extra=0)
#     if request.method == 'POST': # If the form has been submitted...
#         formlist = MappingFormSet(data=request.POST)
#         mappings = []
#         if formlist.is_valid():
#             for form in formlist:
#                 if form.cleaned_data['display'] is True:
#                     mappings.append(form.cleaned_data['mapping'])
#             param_string = '|'.join(mappings)
#             url = url_with_querystring(reverse('edit_mappings'),ref=param_string)
#             return HttpResponseRedirect(url)
#         else:
#             print formlist.errors
#     else:
#         #print 'request.GET: ', request.GET
#         #print 'request: ', request
#         initial_dataset = []
#         if search_path:
#             concepts = ['<%s>' % source for source in search_path]
#             mappings = moq.mappings_by_concept(fuseki_process, concepts)
#         else:
#             mappings = []
#         for mapping in mappings:
#             source_strs = moq.concept_components(fuseki_process, [{'concept': mapping['source']}])
#             target_strs = moq.concept_components(fuseki_process,[{'concept': mapping['target']}])
#             if len(source_strs) != 1 or len(target_strs) != 1:
#                 raise ValueError('one and only one source list and target list is required, but not delivered')
#             sources = source_strs[0]['components'].split('&')
#             if source_strs[0].has_key('cfitems'):
#                 source_view = [','.join([ss.split(';')[1].split('/')[-1] for ss in source_strs[0]['cfitems'].split('&')])]
#             else:
#                 source_view = [source.split('/')[-1] for source in sources]
#             targets = target_strs[0]['components'].split('&')
#             if target_strs[0].has_key('cfitems'):
#                 target_view = [','.join([ts.split(';')[1].split('/')[-1] for ts in target_strs[0]['cfitems'].split('&')])]
#             else:
#                 target_view = [target.split('/')[-1] for target in targets]
#             init = {'mapping':mapping['map'], 'source': '&'.join(source_view), 'target': '&'.join(target_view), 'display': True}
#             initial_dataset.append(init)
#         formlist = MappingFormSet(initial = initial_dataset)
#     context_dict = {
#         'formlist' : formlist,
#         'read_only' : READ_ONLY,
#         }
#     if len(request_search) == 1:
#         create_url = url_with_querystring(reverse('new_mapping'), ref=request_search_path)
#         create = {'url':create_url, 'label':'create a new mapping'}
#         context_dict['create'] = create
#     context = RequestContext(request, context_dict)
#     return render_to_response('form.html', context)

    


# def new_mapping(request):
#     '''form view to create a new mapping record'''
#     ## need to implement the functinoality to
#       ##select the other concept
#       ## reverse direction
#       ## make a pair of mirror mappings
#     request_search_path = request.GET.get('ref', '')
#     request_search_path = urllib.unquote(request_search_path).decode('utf8')
#     request_search = request_search_path.split('|')
#     # dataset = None
#     # if request_search != [u'']:
#     #     fso_dict = collections.defaultdict(list)
#     #     print 'searching'
#     #     search_path = [(param.split(';')[0],param.split(';')[1]) for param in request_search]
#     #     for elem in search_path:
#     #         fso_dict['mr:%slink' % (elem[0].upper())].append('<%s>' % elem[1])
#     #     #linkage = moq.get_linkage(fuseki_process, fso_dict)
#     #     #print 'linkage: ', linkage
#     #     #should only have 1 res > imposed by queries
#     #     #dataset = linkage[0]
#     #     dataset = {'mapping': ""}
#     #     #dataset[
#     # else:
#     #     print 'not searching'
#     #     #redirect to search
#     #     #search_path = [('','')]
#     dataset = {}
#     if request_search != [u'']:
#         dataset['sources'] = request_search[0]
#         if len(request_search) == 2:
#                dataset['targets'] = request_search[1]
    
#     MapForm = forms.MappingNewForm
#     if request.method == 'POST': # If the form has been submitted...
#         form = MapForm(request.POST) # A form bound to the POST data
#         if form.is_valid():
#             print form.cleaned_data
#             process_form(form, request)
#             url = url_with_querystring(reverse('mapping'),ref=request_search_path)
#             return HttpResponseRedirect(url)
#     else:
#         if dataset:
#             form = MapForm(initial=dataset)
#         else:
#             form = MapForm()

#     context = RequestContext(request, {
#         'form':form,
#         })
#     return render_to_response('form.html', context)

    

# def edit_mappings(request):
#     '''form view to edit one or more records, retrieved based on a format specific request'''
#     request_search_path = request.GET.get('ref', '')
#     request_search_path = urllib.unquote(request_search_path).decode('utf8')
#     request_search = request_search_path.split('|')
#     if request_search != [u'']:
#         search_path = request_search
#         #print search_path
#     else:
#         search_path = False#[('','')]
#     pre = prefixes.Prefixes()

#     MappingFormSet = formset_factory(forms.MappingEditForm, extra=0)
#     warning_msg = ''
#     if request.method == 'POST':
#         formset = MappingFormSet(request.POST)
#         if formset.is_valid():
#             # process formset creates a new mapping record for
#             # each form which has changed and returns the list of
#             # mapping IDs for created and unchanged mappings
            
#             query_search_path = process_formset(formset, request)
#             print 'qsp: ', query_search_path.split('|')
#             return HttpResponseRedirect(url_with_querystring(
#                 reverse('edit_mappings'), ref=query_search_path))
#         else:
#             print formset.errors
#     else:
#         map_records = moq.mapping_by_id(fuseki_process, search_path)
#         initial_data_set = []
#         if len(map_records) > 0:
#             for item in map_records:
#                 data_set = {}
#                 mapurl = item.get('map')
#                 source = item.get('source')
#                 if item.get('source_cfitems') is not None:
#                     source_view = ''
#                     cftargets = item.get('source_cfitems').split('&')
#                     for cft in cftargets:
#                         source_view = '|'.join([','.join([ss.split(';')[1].split('/')[-1]
#                                                       for ss in item.get('source_cfitems').split('|')])])
#                 else:
#                     source_view = '&'.join([s.split('/')[-1] for s in item.get('source_comps').split('&')])
#                 target = item.get('target')
#                 if item.get('target_cfitems') is not None:
#                     #target = item.get('target_cfitems')
#                     cftargets = item.get('target_cfitems').split('&')
#                     target_view = ''
#                     for cft in cftargets:
#                         target_view += '|'.join([','.join([ss.split(';')[1].split('/')[-1]
#                                                           for ss in cft.split('|')])])
#                 else:
#                     target_view = '&'.join([t.split('/')[-1] for t in item.get('target_comps').split('&')])
#                 data_set = dict(
#                     mapping = item.get('map'),
#                     last_edit = item.get('creation'),
#                     last_editor = item.get('creator'),
#                     current_status = item.get('status'),
#                     last_comment = item.get('comment'),
#                     last_reason = item.get('reason'),
#                     owners = item.get('owners'),
#                     watchers = item.get('watchers'),
#                     replaces = item.get('replaces'),
#                     #replaces = mark_safe("%s" % replaceslabel),
#                     #replaces = replacesurl,
#                     sources = source,
#                     sources_view = source_view,
#                     targets = target,
#                     targets_view = target_view,
#                     )
#                 initial_data_set.append(data_set)
#         formset = MappingFormSet(initial=initial_data_set)
#     context_dict = {'viewname' : 'Edit Record',
#             'title' : 'Edit Record: %s' % request,
#             'formset' : formset,
#             'read_only' : READ_ONLY,
#             'error' : warning_msg,}
#     context = RequestContext(request, context_dict)
#     return render_to_response('form.html', context)
        

# def process_formset(formset,request):
#     ''' ingest the new or edit form and pass changes to the SPARQL endpoint query as a dictionary'''
#     #for now, assume that the link has not changed, thus mapping record updates only allowed
#     maps = []
#     for form in formset:
#         maps.append(process_form(form, request))
#     mappings = '|'.join(maps)
#     return mappings



              
