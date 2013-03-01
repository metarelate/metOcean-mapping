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
    """
    returns a view for the editor homepage
    a control panel for interacting with the triple store
    and reporting on status
    """
    persist = fuseki_process.query_cache()
    cache_status = '{} statements in the local triple store are' \
                   ' flagged as not existing in the persistent ' \
                   'StaticData store'.format(len(persist))
    cache_state = moq.print_records(persist)
    if request.method == 'POST':
        form = forms.HomeForm(request.POST)
        if form.is_valid():
            invalids = form.cleaned_data.get('validation')
            if invalids:
                # for key in invalids:
                #     invalids[key] = '|'.join([inv['amap'] for
                #                               inv in invalids[key]])
                # request_string = '|'.join([invalids[key] for key in invalids])
                # print request_string
                url = url_with_querystring(reverse('invalid_mappings'),
                                           ref=json.dumps(invalids))
                response = HttpResponseRedirect(url)
            else:
                url = url_with_querystring(reverse('home'))
                response = HttpResponseRedirect(url)
    else:
        form = forms.HomeForm(initial={'cache_status':cache_status,
                                       'cache_state':cache_state})
        con_dict = {}
        searchurl = url_with_querystring(reverse('fsearch'),ref='')
        con_dict['search'] = {'url':searchurl, 'label':'search for mappings'}
        createurl = reverse('mapping_formats')
        con_dict['create'] = {'url':createurl, 'label':'create a new mapping'}
        con_dict['control'] = {'control':'control'}
        con_dict['form'] = form
        context = RequestContext(request, con_dict)
        response = render_to_response('main.html', context)
    return response

def mapping_formats(request):
    """
    returns a view to define the formats for the mapping_concept
    """
    if request.method == 'POST':
        form = forms.MappingFormats(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            referrer = {'mr:source': {'mr:hasFormat': data['source_format']},
                        'mr:target': {'mr:hasFormat': data['target_format']}}
            url = url_with_querystring(reverse('mapping_concepts'),
                                       ref=json.dumps(referrer))
            response = HttpResponseRedirect(url)
    else:
        form = forms.MappingFormats()
        context = RequestContext(request, {'form':form})
        response = render_to_response('simpleform.html', context)
    return response

def _prop_id(members):
    """
    helper method
    returns the value_ids from a list of value records
    in the triple store
    """
    new_map = copy.deepcopy(members)
    property_list = []
    prop_ids = []
    for mem, new_mem in zip(members, new_map):
        comp_mem = mem.get('mr:hasComponent')
        new_comp = new_mem.get('mr:hasComponent')
        if comp_mem and new_comp:
            props = comp_mem.get('mr:hasProperty')
            new_props = new_comp.get('mr:hasProperty')
            if props and new_props:
                for i, (prop, new_prop) in enumerate(zip(props, new_props)):
                    prop_res = moq.get_property(fuseki_process, prop)
                    cpid = '{}'.format(prop_res['property'])
                    #print 'props:', props
                    props[i] = cpid
                    #print 'props:', props
                    #print 'new_props:', new_props
                    new_props[i]['component'] = cpid
                    #print 'new_props:', new_props
            else:
                #validation error please
                raise ValueError('If a property has a component that component'
                                 'must itself reference properties')
            cres = moq.get_component(fuseki_process, comp_mem)
            mem['mr:hasComponent'] = cres['component']
            new_mem['mr:hasComponent']['component'] = cres['component']
        res = moq.get_property(fuseki_process, mem)
        pid = res['property']
        new_mem['property'] = pid
        prop_ids.append(pid)
    return prop_ids, new_map


def url_with_querystring(path, **kwargs):
    """
    helper function
    returns url for path and query string

    """
    return path + '?' + urllib.urlencode(kwargs)


# def _create_concepts(key, request_search, new_map, concepts):
#     """
#     helper to create concepts in the triple store
#     """
#     if isinstance(request_search[key]['skos:member'], list):
#         subc_ids = []
#         for i,member in enumerate(request_search[key]['skos:member']):
#             if member.get('skos:member') is not None:
#                 prop_ids, members = _prop_id(member.get('skos:member'))
#                 sub_concept_dict = {
#                     'mr:format': '<%s>' % request_search[key]['mr:format'],
#                     'skos:member':prop_ids}                    
#                 sub_concept = moq.get_format_concept(fuseki_process,
#                                                      sub_concept_dict)
#                 subc_ids.append('%s' % sub_concept['formatConcept'])
#                 new_map[key]['skos:member'][i]['formatConcept'] = \
#                                 '%s' % sub_concept['formatConcept']
#         prop_ids, members = _prop_id(request_search[key]['skos:member'])
#         concept_dict = {'mr:format':'<%s>' % request_search[key]['mr:format'],
#                                     'skos:member':prop_ids+subc_ids}
#         if request_search[key].get('dc:mediates'):
#             concept_dict['dc:mediates'] = request_search[key]['dc:mediates']
#         if request_search[key].get('dc:requires'):
#             concept_dict['dc:requires'] = request_search[key]['dc:requires']
#         concept = moq.get_format_concept(fuseki_process, concept_dict)
#         if concept:
#             concepts[key] = concept['formatConcept']
#         else:
#             ec = 'formatConcept get did not return 1 id {}'.format(concept)
#             raise ValueError(ec)
#     return new_map, concepts

def _create_components(key, request_search, new_map, components):
    """

    """
    subc_ids = []
    for i, (mem, newm) in enumerate(zip(request_search[key]['mr:hasComponent'],
                                  new_map[key]['mr:hasComponent'])):
        if mem.get('mr:hasProperty'):
            prop_ids, newm[i] = _prop_id(mem.get('mr:hasProperty'))
            sub_concept_dict = {
                'mr:hasFormat': '<%s>' % request_search[key]['mr:hasFormat'],
                'mr:hasProperty':prop_ids}                    
            sub_comp = moq.get_component(fuseki_process,
                                                 sub_concept_dict)
            subc_ids.append('%s' % sub_comp['component'])
            new_map[key]['mr:hasComponent'][i]['component'] = \
                            '%s' % sub_concept['component']
    concept_dict = {'mr:hasFormat':'<%s>' % request_search[key]['mr:hasFormat'],
                                'mr:hasComponent':subc_ids}
    comp = moq.get_component(fuseki_process, comp_dict)
    if comp:
        components[key] = comp['component']
    else:
        ec = 'get_component get did not return 1 id {}'.format(concept)
        raise ValueError(ec)
    return new_map, components

def _create_properties(key, request_search, new_map, components):
    """
    """
    props = request_search[key]['mr:hasProperty']
    prop_ids, new_map[key]['mr:hasProperty'] = _prop_id(props)
    comp_dict = {'mr:hasFormat':'<%s>' % request_search[key]['mr:hasFormat'],
                                'mr:hasProperty':prop_ids}
    if request_search[key].get('dc:mediates'):
        comp_dict['dc:mediates'] = request_search[key]['dc:mediates']
    if request_search[key].get('dc:requires'):
        comp_dict['dc:requires'] = request_search[key]['dc:requires']
    comp = moq.get_component(fuseki_process, comp_dict)
    if comp:
        components[key] = comp['component']
    else:
        ec = 'get_component get did not return 1 id {}'.format(concept)
        raise ValueError(ec)
    return new_map, components


def _component_links(key, request_search, amended_dict):
    """
    helper method
    provides urls in amended_dict for adding and removing concepts
    """
    fformurl = '<%s>' % request_search[key]['mr:hasFormat']
    fformat = request_search[key]['mr:hasFormat'].split('/')[-1]
    ## 'add a new component' link
    fterm = copy.deepcopy(request_search)
    if not fterm[key].get('mr:hasProperty'):
        if not fterm[key].get('mr:hasComponent'):
            fterm[key]['mr:hasComponent'] = []
            amended_dict[key]['mr:hasComponent'] = []
        fterm[key]['mr:hasComponent'].append({"mr:hasComponent":[]})
        refer = {'url': url_with_querystring(reverse('mapping_concepts'),
                                             ref=json.dumps(fterm)),
                'label': 'add a component'}
        amended_dict[key]['mr:hasComponent'].append(refer)
    ## 'add a new property' link if no sub-component exist
    if not request_search[key].get('mr:hasComponent'):
        new_term = copy.deepcopy(request_search)
        if not new_term[key].get('mr:hasProperty'):
            new_term[key]['mr:hasProperty'] = []
            amended_dict[key]['mr:hasProperty'] = []
        new_term[key]['mr:hasProperty'].append('&&&&')
        refer = {'url':url_with_querystring(reverse('define_property',
                      kwargs={'fformat':fformat}),
                      ref=json.dumps(new_term)),
                'label':'add a property definition'}
        amended_dict[key]['mr:hasProperty'].append(refer)
    ## removers
    rem_keys = ['mr:hasProperty', 'mr:hasComponent']
    for rem_key in rem_keys:
        for i, element in enumerate(request_search[key].get(rem_key, [])):
            remover = copy.deepcopy(request_search)
            del remover[key][rem_key][i]
            url = url_with_querystring(reverse('mapping_concepts'),
                                               ref=json.dumps(remover))
            amended_dict[key][rem_key][i]['remove'] = {'url':url,
                                    'label':'remove this item'}
    for i, elem in enumerate(request_search[key].get('mr:hasProperty', [])):
        ## link to add a new component to a 'name only' property
        if elem.get('mr:name') and not elem.get('mr:operator') and not \
            elem.get('rdf:value') and not elem.get('mr:hasComponent'):
            refr = copy.deepcopy(request_search)
            refr[key]['mr:hasProperty'][i]['mr:hasComponent'] = {'mr:hasFormat':fformurl}
            compurl = url_with_querystring(reverse('mapping_concepts'),
                                     ref=json.dumps(refr))
            ref = {'url':compurl, 'label':'add a component'}
            #print ref
            amended_dict[key]['mr:hasProperty'][i]['define_component'] = ref
        #adder for a new sub-conponent property to a name and concept property
        elif elem.get('mr:name') and not elem.get('mr:operator') and not \
            elem.get('rdf:value') and elem.get('mr:hasComponent'):
            refr = copy.deepcopy(request_search)
            if not elem['mr:hasComponent'].get('mr:hasProperty'):
                refr[key]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'] = []
                amended_dict[key]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'] = []
            refr[key]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'].append('&&&&')
            prop = {'url':url_with_querystring(reverse('define_property',
              kwargs={'fformat':fformat}),
              ref=json.dumps(refr)), 'label':'add a property definition'}
            amended_dict[key]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'].append(prop)
            #remover for each sub-component property
            for j, pelem in enumerate(elem['mr:hasComponent'].get('mr:hasProperty', [])):
                remover = copy.deepcopy(request_search)
                del remover[key]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'][j]
                url = url_with_querystring(reverse('mapping_concepts'),
                                                   ref=json.dumps(remover))
                amended_dict[key]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'][j]['remove'] = {'url':url, 'label':'remove this item'}
    ## iterate through sub-components
    for k, scomp in enumerate(request_search[key].get('mr:hasComponent', [])):
        ## add property
        new_term = copy.deepcopy(request_search)
        if not new_term[key]['mr:hasComponent'][k].get('mr:hasProperty'):
            new_term[key]['mr:hasComponent'][k]['mr:hasProperty'] = []
            amended_dict[key]['mr:hasComponent'][k]['mr:hasProperty'] = []
        new_term[key]['mr:hasComponent'][k]['mr:hasProperty'].append('&&&&')
        refer = {'url':url_with_querystring(reverse('define_property',
                      kwargs={'fformat':fformat}),
                      ref=json.dumps(new_term)),
                'label':'add a property definition'}
        amended_dict[key]['mr:hasComponent'][k]['mr:hasProperty'].append(refer)
    ## remove property
        for i, elem in enumerate(request_search[key]['mr:hasComponent'][k].get('mr:hasProperty', [])):
            remover = copy.deepcopy(request_search)
            del remover[key]['mr:hasComponent'][k]['mr:hasProperty'][i]
            url = url_with_querystring(reverse('mapping_concepts'),
                                               ref=json.dumps(remover))
            amended_dict[key]['mr:hasComponent'][k]['mr:hasProperty'][i]['remove'] = {'url':url,
                                    'label':'remove this item'}
            ## enable component as property
            if elem.get('mr:name') and not elem.get('mr:operator') and not \
                elem.get('rdf:value') and not elem.get('mr:hasComponent'):
                refr = copy.deepcopy(request_search)
                refr[key]['mr:hasComponent'][k]['mr:hasProperty'][i]['mr:hasComponent'] = {'mr:hsFormat':fformurl}
                compurl = url_with_querystring(reverse('mapping_concepts'),
                                         ref=json.dumps(refr))
                ref = {'url':compurl, 'label':'add a component'}
                #print ref
                amended_dict[key]['mr:hasComponent'][k]['mr:hasProperty'][i]['define_component'] = ref
            elif elem.get('mr:name') and not elem.get('mr:operator') and not \
                elem.get('rdf:value') and elem.get('mr:hasComponent'):
                #adder for a new property
                refr = copy.deepcopy(request_search)
                if not elem['mr:hasComponent'].get('mr:hasProperty'):
                    refr[key]['mr:hasComponent'][k]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'] = []
                    amended_dict[key]['mr:hasComponent'][k]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'] = []
                refr[key]['mr:hasComponent'][k]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'].append('&&&&')
                prop = {'url':url_with_querystring(reverse('define_property',
                  kwargs={'fformat':fformat}),
                  ref=json.dumps(refr)), 'label':'add a property definition'}
                amended_dict[key]['mr:hasComponent'][k]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'].append(prop)
                #remover for each property
                for j, pelem in enumerate(elem['mr:hasComponent'].get('mr:hasProperty', [])):
                    remover = copy.deepcopy(request_search)
                    del remover[key]['mr:hasComponent'][k]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'][j]
                    url = url_with_querystring(reverse('mapping_concepts'),
                                                       ref=json.dumps(remover))
                    amended_dict[key]['mr:hasComponent'][k]['mr:hasProperty'][i]['mr:hasComponent']['mr:hasProperty'][j]['remove'] = {'url':url, 'label':'remove this item'}
    ## mediators
    for fckey in ['dc:requires', 'dc:mediates']:
        url = None
        if fformat == 'cf':
            adder = copy.deepcopy(request_search)
            if request_search[key].get(fckey):
                if fckey == 'dc:requires':
                    adder[key][fckey].append('&&&&')
                    url = url_with_querystring(reverse('define_mediator',
                                                       kwargs={'mediator':fckey,
                                                        'fformat':fformat}),
                                                        ref=json.dumps(adder))
            else:
                adder[key][fckey] = ['&&&&']
                url = url_with_querystring(reverse('define_mediator', kwargs=
                                                   {'mediator':fckey,
                                                    'fformat':fformat}),
                                                    ref=json.dumps(adder))
                amended_dict[key][fckey] = []
            if url:
                amended_dict[key][fckey].append({'url': url, 'label':
                                                 'add a {}'.format(fckey)}) 

    return amended_dict


def mapping_concepts(request):
    """
    returns a view to present the mapping concepts:
    source and target, and the valuemaps
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request_search_path == '':
        request_search_path = '{}'
    request_search = json.loads(request_search_path)
    amended_dict = copy.deepcopy(request_search)
    if request.method == 'POST':
        ## get the formatConcepts for source and target
        ## pass to value map definition
        form = forms.MappingConcept(request.POST)
        components = {}
        new_map = copy.deepcopy(request_search)
        for key in ['mr:source','mr:target']:
            if request_search[key].get('mr:hasProperty'):
                new_map, components = _create_properties(key, request_search,
                                                         new_map, components)
            elif request_search[key].get('mr:hasComponent'):
                new_map, components = _create_components(key, request_search,
                                                         new_map, components)
        for key in ['mr:source','mr:target']:
            if components.has_key(key):
                new_map[key]['component'] = '%s' % components[key]
            else:
                raise ValueError('The source and target are not both defined')
        ref = json.dumps(new_map)
        url = url_with_querystring(reverse('value_maps'),ref=ref)
        response = HttpResponseRedirect(url)
    else:
        form = forms.MappingConcept()
        for key in ['mr:source','mr:target']:
            amended_dict = _component_links(key, request_search, amended_dict)
        con_dict = {}
        con_dict['mapping'] = amended_dict
        con_dict['form'] = form
        context = RequestContext(request, con_dict)
        response = render_to_response('mapping_concept.html', context)
    return response

def define_mediator(request, mediator, fformat):
    """
    returns a view to define a mediator for a
    formatConcept
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = json.loads(request_search_path)
    if request.method == 'POST':
        form = forms.Mediator(request.POST, fformat=fformat)
    else:
        form = forms.Mediator(fformat=fformat)
    if request.method == 'POST' and form.is_valid():
        mediator = form.cleaned_data['mediator']
        request_search_path = request_search_path.replace('&&&&',
                                                          mediator)
        # request_search_path = json.dumps(request_search)
        url = url_with_querystring(reverse('mapping_concepts'),
                                   ref=request_search_path)
        response = HttpResponseRedirect(url)
        #return HttpResponseRedirect(url)
    else:
        # form = forms.Mediator(fformat=fformat)
        con_dict = {'form':form}
        if mediator == 'dc:mediates':
            links = []
            link_url = url_with_querystring(reverse('create_mediator', kwargs={'fformat':fformat}),
                                            ref=request_search_path)
            links.append({'url':link_url, 'label':'create a new mediator'})
            con_dict['links'] = links
        context = RequestContext(request, con_dict)
        response = render_to_response('simpleform.html', context)
    return response


def create_mediator(request, fformat):
    """
    returns a view to define a mediator for a
    formatConcept
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = json.loads(request_search_path)
    if request.method == 'POST':
        form = forms.NewMediator(request.POST)
    else:
        form = forms.NewMediator()
    if request.method == 'POST' and form.is_valid():
        mediator = form.cleaned_data['mediator']
        moq.create_mediator(fuseki_process, mediator, fformat)
        kw = {'mediator':'dc:mediates','fformat':fformat}
        url = url_with_querystring(reverse('define_mediator', kwargs=kw),
                                   ref=request_search_path)
        response = HttpResponseRedirect(url)
    else:
        con_dict = {'form':form}
        context = RequestContext(request, con_dict)
        response = render_to_response('simpleform.html', context)
    return response


def _get_value(value):
    """
    returns a value id for a given json input
    """
    id_value = copy.deepcopy(value)
    #fragile, doesn't work for nested values
    prop = moq.get_property(fuseki_process,
                               value['mr:subject']['mr:hasProperty'])
    sc_prop = moq.get_scoped_property(fuseki_process,
                                      {'mr:hasProperty':prop['property'],
                                    'mr:scope':value['mr:subject']['mr:scope']})
    new_val = {'mr:subject':sc_prop['scopedProperty']}
    if value.get('mr:object'):
        oprop = moq.get_property(fuseki_process,
                               value['mr:object']['mr:hasProperty'])
        o_sc_prop = moq.get_scoped_property(fuseki_process,
                                      {'mr:hasProperty':oprop['property'],
                                    'mr:scope':value['mr:object']['mr:scope']})
        new_val['mr:object'] = o_sc_prop['scopedProperty'] 
    if value.get('mr:operator'):
        new_val['mr:operator'] = value.get('mr:operator')
    value =  moq.get_value(fuseki_process, new_val)
    v_id = value['value']
    return v_id
        

def value_maps(request):
    """
    returns a view to define value mappings for a defined
    source and target pair
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request_search_path == '':
        request_search_path = '{}'
    request_search = json.loads(request_search_path)
    print request_search
    amended_dict = copy.deepcopy(request_search)
    if request.method == 'POST':
        ## create the valuemaps as defined
        ## check if a mapping (including invalid) provides this source to target
        #### or this source to a different target (same format)
        #### perhaps render this on a new screen
        ## then pass the json of {source:{},target:{},valueMaps[{}]
        ## to mapping_edit for creation
        form = forms.MappingConcept(request.POST)
        for valuemap in request_search.get('mr:hasValueMap',[]):
            # vmap = moq.get_value_map(fuseki_process, valmap)
            vmap_dict = {'mr:source':_get_value(valuemap['mr:source']),
                         'mr:target':_get_value(valuemap['mr:target'])}
            vmap = moq.get_value_map(fuseki_process, vmap_dict)
            valuemap['valueMap'] = vmap['valueMap']
            #value['value'] = val_id
        url = url_with_querystring(reverse('mapping_edit'),
                                   ref = json.dumps(request_search))
        response = HttpResponseRedirect(url)
            
    else:
        form = forms.MappingConcept()
        if not amended_dict.has_key('mr:hasValueMap'):
            addition = copy.deepcopy(request_search)
            addition['mr:hasValueMap'] = []
            url = url_with_querystring(reverse('define_valuemaps'),
                                       ref=json.dumps(addition))
            amended_dict['addValueMap'] = {'url':url,
                                           'label':'add a value mapping'}
        else:
            url = url_with_querystring(reverse('define_valuemaps'),
                                       ref=json.dumps(request_search))
            amended_dict['addValueMap'] = {'url':url,
                                           'label':'add a value mapping'}
        con_dict = {}
        con_dict['mapping'] = amended_dict
        con_dict['form'] = form
        context = RequestContext(request, con_dict)
        response = render_to_response('mapping_concept.html', context)
    return response

def _define_valuemap_choice(comp, aproperty, choice):
    """
    """
    pcomp = aproperty.get('mr:hasComponent')
    if not aproperty.get('rdf:value') and not pcomp:
        choice[1].append(json.dumps({'mr:subject':{'mr:scope':comp, 
                           'mr:hasProperty': {'mr:name':aproperty.get('mr:name')}}}))
    elif pcomp:
        for prop in pcomp.get('mr:hasProperty', []):
            if not prop.get('rdf:value'):
                val = json.dumps({'mr:subject':{'mr:scope':pcomp.get('component'), 
                           'mr:hasProperty': {'mr:name': aproperty.get('mr:name')}}})
                choice[1].append(val)
    return choice

def define_valuemap(request):
    """
    returns a view to input choices for an individual value_map
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = json.loads(request_search_path)
    #print request_search
    source_list = []
    target_list = []
    choices = [('mr:source', source_list),('mr:target', target_list)]
    for i, ch in enumerate(choices):
        if request_search[ch[0]].get('mr:hasProperty'):
            comp = request_search[ch[0]]['component']
            for elem in request_search[ch[0]]['mr:hasProperty']:
                choices[i] = _define_valuemap_choice(comp, elem, ch)
        elif request_search[ch[0]].get('mr:hasComponent'):
            for elem in request_search[ch[0]]['mr:hasComponent']:
                comp = elem['component']
                for selem in elem['mr:hasProperty']:
                    choices[i] = _define_valuemap_choice(comp, selem, ch)
        if request_search.get('derived_values'):
            for derived in request_search['derived_values'].get(ch[0]):
                ch[1].append(json.dumps(derived))
    if request.method == 'POST':
        form = forms.ValueMap(request.POST, sc=source_list, tc=target_list)
        if form.is_valid():
            source = json.loads(form.cleaned_data['source_value'])
            target = json.loads(form.cleaned_data['target_value'])
            new_vmap = {'mr:source':source,
                        'mr:target':target}
            request_search['mr:hasValueMap'].append(new_vmap)
            if request_search.get('derived_values'):
                del request_search['derived_values']
                # {'mr:sourceFC':source[0],
                #                                   'mr:sourceVal':source[1],
                #                                   'mr:targetFC':target[0],
                #                                   'mr:targetVal':target[1]})
            request_search_path = json.dumps(request_search)
            url = url_with_querystring(reverse('value_maps'),
                                       ref=request_search_path)
            return HttpResponseRedirect(url)
    else:
        form = forms.ValueMap(sc=source_list, tc=target_list)
    con_dict = {'form':form}
    links = []
    link_url = url_with_querystring(reverse('derived_value', kwargs={'role':'source'}),
                                        ref=request_search_path)
    links.append({'url':link_url, 'label':'create a derived source value'})
    link_url = url_with_querystring(reverse('derived_value', kwargs={'role':'target'}),
                                        ref=request_search_path)
    links.append({'url':link_url, 'label':'create a derived target value'})
    con_dict['links'] = links
    context = RequestContext(request, con_dict)
    return render_to_response('simpleform.html', context)


def derived_value(request, role):
    """
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    request_search = json.loads(request_search_path)
    if not request_search.get('derived_values'):
        request_search['derived_values'] = {'mr:source':[], 'mr:target':[]}
    source_list = []
    target_list = []
    choices = [('mr:source', source_list),('mr:target', target_list)]
    for i, ch in enumerate(choices):
        if request_search[ch[0]].get('mr:hasProperty'):
            comp = request_search[ch[0]]['component']
            for elem in request_search[ch[0]]['mr:hasProperty']:
                choices[i] = _define_valuemap_choice(comp, elem, ch)
        elif request_search[ch[0]].get('mr:hasComponent'):
            for elem in request_search[ch[0]]['mr:hasComponent']:
                comp = elem['component']
                for selem in elem['mr:hasProperty']:
                    choices[i] = _define_valuemap_choice(comp, selem, ch)
    if role == 'source':
        components = source_list
    elif role == 'target':
        components = target_list
    else:
        raise ValueError('role must be source or target')
    if request.method == 'POST':
        form = forms.DerivedValue(request.POST, components=components)
        if form.is_valid():
            derived_val = json.loads(form.cleaned_data['_subject'])
            derived_val['mr:object'] = json.loads(form.cleaned_data['_object'])['mr:subject']
            derived_val['mr:operator'] = form.cleaned_data['_operator']
            request_search['derived_values']['mr:{}'.format(role)].append(derived_val)
            request_search_path = json.dumps(request_search)
            url = url_with_querystring(reverse('define_valuemaps'),
                                       ref=request_search_path)
            response = HttpResponseRedirect(url)
        else:
            con_dict = {'form':form}
            context = RequestContext(request, con_dict)
            response = render_to_response('simpleform.html', context)
    else:
        form = forms.DerivedValue(components=components)
        con_dict = {'form':form}
        context = RequestContext(request, con_dict)
        response = render_to_response('simpleform.html', context)
    return response


def define_property(request, fformat):
    """
    returns a view to define an individual property
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request.method == 'POST':
        form = forms.Value(request.POST, fformat=fformat)
        if form.is_valid():
            new_value = {}
            if form.cleaned_data.get('name'):
                new_value['mr:name'] = form.cleaned_data['name']
            if form.cleaned_data['value'] != '""':
                new_value['rdf:value'] =  form.cleaned_data['value']
            if form.cleaned_data.get('operator'):
                new_value['mr:operator'] = form.cleaned_data['operator']
            newv = json.dumps(new_value)
            request_search_path = request_search_path.replace('"&&&&"', newv)
            url = url_with_querystring(reverse('mapping_concepts'),
                                       ref=request_search_path)
            response = HttpResponseRedirect(url)
        else:
            con_dict = {'form':form}
            context = RequestContext(request, con_dict)
            response = render_to_response('simpleform.html', context)
    else:
        form = forms.Value(fformat=fformat)
        con_dict = {'form':form}
        context = RequestContext(request, con_dict)
        response = render_to_response('simpleform.html', context)
    return response


# def define_concept(request, fformat):
#     """
#     returns a view to define an indivdual  concept
#     """
#     request_search_path = request.GET.get('ref', '')
#     request_search_path = urllib.unquote(request_search_path).decode('utf8')
#     if request.method == 'POST':
#         form = forms.FormatConcept(request.POST, fformat=fformat)
#         if form.is_valid():
#             new_value = {'skos:member':[{}]}
#             newv = json.dumps(new_value)
#             request_search_path = request_search_path.replace('"&&&&"', newv)
#             url = url_with_querystring(reverse('mapping_concepts'),
#                                        ref=request_search_path)
#             response = HttpResponseRedirect(url)
#     else:
#         form = forms.FormatConcept(fformat=fformat)
#         con_dict = {'form':form}
#         context = RequestContext(request, con_dict)
#         response = render_to_response('simpleform.html', context)
#     return response

    
def mapping_edit(request):
    """
    returns a view to provide editing to the mapping record defining a
    source target and any valuemaps from the referrer
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request_search_path == '':
        request_search_path = '{}'
    request_search = json.loads(request_search_path)
    # print request_search
    if request.method == 'POST':
        form = forms.MappingMeta(request.POST)
        if form.is_valid():
            map_id = process_form(form, request_search_path)
            request_search['mapping'] = map_id
            url = url_with_querystring(reverse('mapping_edit'),
                                       ref=json.dumps(request_search))
            return HttpResponseRedirect(url)
    else:
        ## look for mapping, if it exists, show it, with a warning
        ## if a partially matching mapping exists, handle this (somehow)
        initial = {'invertible':True,
                   'source':request_search.get('mr:source').get('component')
                   ,
                   'target':request_search.get('mr:target').get('component')
                   , 'valueMaps':'&'.join([vm.get('valueMap') for vm
                                         in request_search.get('mr:hasValueMap',
                                                               [])])}
        # print 'initial:  ', initial
        map_id = request_search.get('mapping')
        if map_id:
            mapping = moq.get_mapping_by_id(fuseki_process, map_id)
            # print 'mapping:', mapping
            # print 'initial:', initial
            ts = initial['source'] == mapping['source']
            tt = initial['target'] == mapping['target']
            tvm = initial['valueMaps'].split('&').sort() == \
                  mapping.get('hasValueMaps', '').split('&').sort()
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
    data = form.cleaned_data
    mapping_p_o = collections.defaultdict(list)
    ## take the new values from the form and add all of the initial values
    ## not included in the 'remove' field
    for label in ['owner','watcher']:
        #data = form.cleaned_data
        #if data['add_()s'.format(label)] != '':
        if data['add_%ss' % label] != '':
            for val in data['add_%ss' % label].split(','):
                mapping_p_o['mr:%s' % label].append('"%s"' % val)
        if data['%ss' % label] != '':
            for val in data['%ss' % label].split(','):
                if val not in data['remove_%ss' % label].split(',') and\
                    val not in mapping_p_o['mr:%s' % label].split(','):
                    mapping_p_o['mr:%s' % label].append('"%s"' % val)
        #if len(mapping_p_o['mr:%s' % label]) == 0:
        #    mapping_p_o['mr:%s' % label] = ['"None"']

    mapping_p_o['dc:creator'] = ['%s' % data['editor']]
    mapping_p_o['dc:date'] = ['"%s"^^xsd:dateTime' % globalDateTime]
    mapping_p_o['mr:status'] = ['"%s"' % data['next_status']]
    if data['mapping'] != "":
        mapping_p_o['dc:replaces'] = ['%s' % data['mapping']]
    if data['comment'] != '':
        mapping_p_o['skos:note'] = ['"%s"' % data['comment']]
    mapping_p_o['mr:reason'] = ['"%s"' % data['next_reason']]
    mapping_p_o['mr:source'] = ['%s' % data['source']]
    mapping_p_o['mr:target'] = ['%s' % data['target']]
    mapping_p_o['mr:invertible'] = ['"%s"' % data['invertible']]
    if data.get('valueMaps'):
        mapping_p_o['mr:hasValueMap'] = ['%s' % vm for vm in
                                  data['valueMaps'].split('&')]

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

    mapping = mapping_p_o
    mapping = moq.create_mapping(fuseki_process, mapping_p_o,True)
    map_id = mapping[0]['map']

    return map_id


def invalid_mappings(request):
    """
    list mappings which reference the concept search criteria
    by concept by source then target
    """
    request_search_path = request.GET.get('ref', '')
    request_search_path = urllib.unquote(request_search_path).decode('utf8')
    if request_search_path == '':
        request_search_path = '{}'
    request_search = json.loads(request_search_path)
    invalids = []
    for key, inv_mappings in request_search.iteritems():
        invalid = {'label':key, 'mappings':[]}
        for inv_map in inv_mappings:
            mapping = moq.get_mapping_by_id(fuseki_process, inv_map['amap'])
            referrer = fuseki_process.structured_mapping(mapping)
            map_json = json.dumps(referrer)
            url = url_with_querystring(reverse('mapping_edit'), ref=map_json)
            sig = inv_map.get('signature', [])
            label = []
            if isinstance(sig, list):
                for elem in sig:
                    label.append(elem.split('/')[-1].strip('<>'))
            else:
                label.append(sig.split('/')[-1].strip('<>'))
            if label:
                '&'.join(label)
            else:
                label = 'mapping'
            invalid['mappings'].append({'url':url, 'label':label})
        invalids.append(invalid)
    context_dict = {'invalid': invalids}
    context = RequestContext(request, context_dict)
    return render_to_response('select_list.html', context)


    
##### non-functional: not for review ####################################


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
            response = HttpResponseRedirect(url)
    else:
        form = Searchform()
        context = RequestContext(request, {
            'form':form,
            })
        response = render_to_response('form.html', context)
    return response

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
            response = HttpResponseRedirect(url)
    else:
        form = Searchform()
        context = RequestContext(request, {
            'form':form,
            })
        response = render_to_response('form.html', context)
    return response


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
            response = HttpResponseRedirect(redirect)
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
        response = render_to_response('form.html', context)
    return response


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
            response = HttpResponseRedirect(url)
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
        response = render_to_response('form.html', context)
    return response

              
