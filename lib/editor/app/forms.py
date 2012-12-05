
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

import datetime
from string import Template
import sys
import time

from django import forms
from django.core.urlresolvers import reverse
from django.utils import formats
from django.utils.safestring import mark_safe


import metocean.prefixes as prefixes
import metocean.queries as moq
from settings import READ_ONLY
from settings import fuseki_process

class SearchParam(forms.Form):
    '''
    '''
    parameter = forms.ChoiceField()
    def __init__(self,  *args, **kwargs):
        super(SearchParam, self).__init__(*args, **kwargs)
        choices = (('', ''),
                   ('http://i.am.a/avocet', 'avocet'),
                   ('http://i.am.a/beaver', 'beaver'),
                   ('http://i.am.a/cheetah', 'cheetah'),
                   ('http://i.am.a/dugong', 'dugong'),
                   ('http://i.am.a/emu', 'emu'))
        #define choices
        #if dataFormat == 'um' and qualifier:
        #print self.fields
        self.fields['parameter'].choices = choices
    # def clean(self):
    #     return self.cleaned_data

class UMParam(forms.Form):
    '''A django form for adding UM elements to a linkage search path
    '''
    parameter = forms.ChoiceField()
    def __init__(self,  *args, **kwargs):
        super(UMParam, self).__init__(*args, **kwargs)
        stashRes = moq.subject_by_graph(fuseki_process, 'http://um/stashconcepts.ttl')
        #define choices
        choices = [('um;' + stash['subject'], stash['subject'].split('/')[-1]) for stash in stashRes]
        

        self.fields['parameter'].choices = choices

class GRIBParam(forms.Form):
    '''A django form for adding GRIB elements to a linkage search path
    '''
    parameter = forms.ChoiceField()
    def __init__(self,  *args, **kwargs):
        super(GRIBParam, self).__init__(*args, **kwargs)
        gribRes = moq.subject_by_graph(fuseki_process, 'http://grib/codesflags.ttl')
        #define choices
        choices = [('grib;' + grib['subject'], grib['subject']) for grib in gribRes]
        

        self.fields['parameter'].choices = choices

            
class CFParam(forms.Form):
    '''A django form for adding CF elements to a linkage search path
    '''
    parameter = forms.CharField(max_length=100, required=False)
    cf_type = forms.ChoiceField(choices=[('Field','Field')], required=False)
    standard_name = forms.ChoiceField(required=False)
    long_name = forms.CharField(max_length=50, required=False)
    units = forms.CharField(max_length=16, required=False)
    
    def __init__(self,  *args, **kwargs):
        super(CFParam, self).__init__(*args, **kwargs)
        snRes = moq.subject_by_graph(fuseki_process, 'http://CF/cf-standard-name-table.ttl')
        #define choices
        choices = [(name['subject'],name['subject'].split('/')[-1]) for name in snRes]

        self.fields['standard_name'].choices = choices
        self.fields['parameter'].widget = forms.HiddenInput()
        
    def clean(self):
        cleaned_data = super(CFParam, self).clean()
        pred_obj = {}
        pred_obj['mrcf:type'] = '"%s"' % cleaned_data.get('cf_type')
        if cleaned_data.get('standard_name') != 'http://cf-pcmdi.llnl.gov/documents/':
            pred_obj['mrcf:standard_name'] = '<%s>' % cleaned_data.get('standard_name')
        if cleaned_data.get('long_name') != '':
            pred_obj['mrcf:long_name'] = '"%s"' % cleaned_data.get('long_name')
        if cleaned_data.get('units') != '':
            pred_obj['mrcf:units'] = '"%s"' % cleaned_data.get('units')
        # print repr(pred_obj)
        cfres = moq.get_cflinks(fuseki_process, pred_obj)
        # print 'cfres: ', cfres
        if not cfres:
            #if there is no result returned from the query, then create the record and rerun the query
            cfres = moq.create_cflink(fuseki_process, pred_obj, 'http://www.metarelate.net/metocean/cf')
            #cfres = moq.get_cflinks(fuseki_process, pred_obj)
        # print len(cfres)
        # print 'cfres: ', cfres
        if len(cfres) == 1:
            # assign the single result to be returned by the function
            cflink = cfres[0]['s']
        else:
            cflink = ''
        cleaned_data['parameter'] = 'cf;'+cflink
        # print 'cflink: ',cflink
        return cleaned_data
        




def get_states():

    STATES = (
        'Draft',
        'Proposed',
        'Approved',
        'Broken',
        'Deprecated',
    )
    return STATES

def get_reasons():

    REASONS = (
        'new mapping',
        'added metadata',
        'corrected metadata',
        'linked to new format',
        'corrected links',
        'changed status'
        )
    return REASONS



class URLwidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        if value in ('None', None):
            tpl = value
        else:
            tpl = u'<a href="%s">%s</a>' % (reverse('mapdisplay', 
                kwargs={'hashval' : value}), "go to replaces")
        return mark_safe(tpl)

    def clean(self):
        return self.cleaned_data


class ContactForm(forms.Form):
    required_css_class = 'required'
    error_css_class = 'error'
    isoformat = ("%Y-%m-%dT%H:%M:%S.%f",)
    github_name = forms.CharField(max_length=50)
    register = forms.ChoiceField(choices=(('http://www.metarelate.net/metOcean/people','people'),('http://www.metarelate.net/metOcean/organisations','organisations')))


    def clean(self):
        if READ_ONLY:
            raise ValidationError('System in Read-Only mode') 
        else:
            return self.cleaned_data




class MappingEditForm(forms.Form):
    required_css_class = 'required'
    error_css_class = 'error'
    isoformat = "%Y-%m-%dT%H:%M:%S.%f"
    mapping = forms.CharField(max_length=200)
    linkage = forms.CharField(max_length=200)
    last_edit = forms.CharField(max_length=50, required=False)
    last_editor = forms.CharField(max_length=50)
    #editor = forms.CharField(max_length=50, required=False)
    editor = forms.ChoiceField([(r['s'],r['s'].split('/')[-1]) for r in moq.get_contacts(fuseki_process, 'people')])
#    editor = forms.ChoiceField([(r['s'],r['s'].split('/')[-1]) for r in moq.get_contacts('people')], widget=SelectWithPopUp)
    last_comment = forms.CharField(max_length=200)
    comment = forms.CharField(max_length=200,required=False)
    last_reason = forms.CharField(max_length=50)
    reason = forms.ChoiceField(choices=[(x,x) for x in get_reasons()])
    owners = forms.CharField(max_length=200)
    add_owners = forms.CharField(max_length=200, required=False)
    remove_owners = forms.CharField(max_length=200, required=False)
    watchers = forms.CharField(max_length=200)
    add_watchers = forms.CharField(max_length=200, required=False)
    remove_watchers = forms.CharField(max_length=200, required=False)
    replaces = forms.CharField(max_length=128, required=False)
    current_status = forms.CharField(max_length=15)
    next_status = forms.ChoiceField(choices=[(x,x) for x in get_states()])
    cflinks = forms.CharField(max_length=1000, required=False)
    umlinks = forms.CharField(max_length=1000, required=False)
    griblinks  = forms.CharField(max_length=1000, required=False)

    def __init__(self, *args, **kwargs):
        super(MappingEditForm, self).__init__(*args, **kwargs)
        #pre = prefixes.Prefixes()
        self.fields['current_status'].widget.attrs['readonly'] = True
        self.fields['owners'].widget.attrs['readonly'] = True
        self.fields['watchers'].widget.attrs['readonly'] = True
        self.fields['last_edit'].widget.attrs['readonly'] = True
        self.fields['last_editor'].widget.attrs['readonly'] = True
        self.fields['last_comment'].widget.attrs['readonly'] = True
        self.fields['last_reason'].widget.attrs['readonly'] = True
        #self.fields['replaces'].widget = URLwidget()
        self.fields['mapping'].widget.attrs['readonly'] = True
        self.fields['linkage'].widget = forms.HiddenInput()
        self.fields['cflinks'].widget = forms.HiddenInput()
        self.fields['umlinks'].widget = forms.HiddenInput()
        self.fields['griblinks'].widget = forms.HiddenInput()
        if kwargs.has_key('initial'):
            self.expand_links(kwargs, 'cflinks')
            self.expand_links(kwargs, 'umlinks')
            self.expand_links(kwargs, 'griblinks')


    def clean(self):
        if READ_ONLY:
            raise ValidationError('System in Read-Only mode') 
        else:
            return self.cleaned_data


    def expand_links(self, kwargs, name):
        links = None
        if kwargs['initial'].has_key(name):
            links = kwargs['initial'][name]
        name = name.rstrip('s')
        if links:
            for i, link in enumerate(links.split('&')):
                if name == 'cflink':
                    for k,v in moq.get_cflink_by_id(fuseki_process, link)[0].iteritems():
                        self.fields['%s%i_%s' % (name, i, k)] = forms.URLField(initial=v)
                        self.fields['%s%i_%s' % (name, i, k)].widget.attrs['readonly'] = True
                        self.fields['%s%i_%s' % (name, i, k)].widget.attrs['size'] = 50
                else:
                    self.fields['%s%i' % (name, i)] = forms.URLField(initial=link)
                    self.fields['%s%i' % (name, i)].widget.attrs['readonly'] = True
                    self.fields['%s%i' % (name, i)].widget.attrs['size'] = 50



class MappingNewForm(MappingEditForm):
    reason = forms.CharField(max_length=15, initial='new mapping')
    next_status = forms.CharField(max_length=15, initial='Draft')

    def __init__(self, *args, **kwargs):
        super(MappingNewForm, self).__init__(*args, **kwargs)
        self.fields['mapping'].required = False
        self.fields['mapping'].widget = forms.HiddenInput()
        self.fields['last_edit'].widget = forms.HiddenInput()
        self.fields['last_edit'].required = False
        self.fields['last_editor'].widget = forms.HiddenInput()
        self.fields['last_editor'].required = False
        self.fields['last_comment'].widget = forms.HiddenInput()
        self.fields['last_comment'].required = False
        self.fields['last_reason'].widget = forms.HiddenInput()
        self.fields['last_reason'].required = False
        self.fields['owners'].widget = forms.HiddenInput()
        self.fields['owners'].required = False
        self.fields['remove_owners'].widget = forms.HiddenInput()
        self.fields['watchers'].widget = forms.HiddenInput()
        self.fields['watchers'].required = False
        self.fields['remove_watchers'].widget = forms.HiddenInput()
        self.fields['current_status'].widget = forms.HiddenInput()
        self.fields['current_status'].required = False
        self.fields['reason'].widget.attrs['readonly'] = True
        self.fields['next_status'].widget.attrs['readonly'] = True
        if kwargs.has_key('initial'):
            self.expand_links(kwargs, 'cflinks')
            self.expand_links(kwargs, 'umlinks')
            self.expand_links(kwargs, 'griblinks')
        
        
