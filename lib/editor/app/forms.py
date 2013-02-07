
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

def get_states():
    """
    helper method to return valid states
    (consider storing these in the triple store and
    providing access via a query)
    """
    STATES = (
        'Draft',
        'Proposed',
        'Approved',
        'Broken',
        'Deprecated',
    )
    return STATES

def get_reasons():
    """
    helper method to return valid reasons
    (consider storing these in the triple store and
    providing access via a query)
    """
    REASONS = (
        'new mapping',
        'added metadata',
        'corrected metadata',
        'linked to new format',
        'corrected links',
        'changed status'
        )
    return REASONS


def formats():
    """temporary, returns formats
    These should be stored in the triple store and
    provided by a query"""
    format_choices = [('http://metarelate.net/metocean/format/grib', 'GRIB'),
               ('http://metarelate.net/metocean/format/um', 'UM'),
               ('http://metarelate.net/metocean/format/cf', 'CF')]
    return format_choices

class MappingFormats(forms.Form):
    """
    form to define the file format of the source and target
    for a mapping
    """
    source_format = forms.ChoiceField(choices=formats())
    target_format = forms.ChoiceField(choices=formats())
    def clean(self):
        data = self.cleaned_data
        if data['source_format'] == data['target_format']:
            raise forms.ValidationError(
                'The source and target formats must be different')
        return self.cleaned_data


class Mediator(forms.Form):
    """
    form to select a mediator from the list of mediators
    """
    mediator = forms.ChoiceField()
    def __init__(self, *args, **kwargs):
        fformat = kwargs.pop('fformat')
        super(Mediator, self).__init__(*args, **kwargs)
        #meds = moq.get_mediators(fuseki_process, fformat)['med']
        meds = [('<http://www.metarelate.net/metocean/mediates/cf/calendar>',
                 'calendar')]
        self.fields['mediator'].choices = meds

class MappingConcept(forms.Form):
    """
    form to define the concepts for a mapping
    the work of the form is handled by the json
    in the referrer, not the form class
    """
    def clean(self):
        return self.cleaned_data

class Value(forms.Form):
    """
    form to define a value for use in a concept
    """
    #vproperty =  forms.ChoiceField()
    name =  forms.CharField(required=False,
                                 widget=forms.TextInput(attrs={'size':'100'}))
    value = forms.CharField(required=False)
    operator = forms.CharField(required=False)
    
    def __init__(self, *args, **kwargs):
        fformat = kwargs.pop('fformat')
        super(Value, self).__init__(*args, **kwargs)
        op_url = '<http://www.openmath.org/cd/relation1.xhtml#eq>'
        self.fields['operator'].initial = op_url
        if fformat == 'um':
            F3 = '<http://reference.metoffice.gov.uk/def/um/umdp/F3/>'
            self.fields['name'].initial = F3
            # umRes = moq.subject_and_plabel(fuseki_process,
                                         # 'http://um/umdpF3.ttl')
            # choices = [(um['subject'], um['prefLabel'] for um in umRes]
            # self.fields['vproperty'].choices = choices
        elif fformat == 'cf':
            CF = '<http://def.cfconventions.org/data_model/>'
            self.fields['name'].initial = CF
            # cfRes = moq.subject_and_plabel(fuseki_process,
                                         # 'http://CF/cfmodel.ttl')
            # choices = [(cf['subject'], cf['prefLabel'] for cf in cfRes]
            # self.fields['vproperty'].choices = choices
        elif fformat == 'grib':
            GRIB = '<http://def.ecmwf.int/api/grib/keys/>'
            self.fields['name'].initial = GRIB
            # grRes = moq.subject_and_plabel(fuseki_process,
                                           # 'http://grib/gribapi.ttl')
            # choices = [(grib['subject'], grib['prefLabel'] for grib in grRes]
            # self.fields['vproperty'].choices = choices
    def clean(self):
        try:
            int(self.cleaned_data['value'])
        except ValueError:
            if self.cleaned_data['value'].startswith('http'):
                self.cleaned_data['value'] = '<{}>'.format(
                                                self.cleaned_data['value'])
            else:
                self.cleaned_data['value'] = '"{}"'.format(
                                                self.cleaned_data['value'])
        return self.cleaned_data


class ValueMap(forms.Form):
    """
    form to define a value map
    """
    source_value = forms.ChoiceField()
    target_value = forms.ChoiceField()
    def __init__(self, *args, **kwargs):
        sc = kwargs.pop('sc')
        tc = kwargs.pop('tc')
        super(ValueMap, self).__init__(*args, **kwargs)
        self.fields['source_value'].choices = sc
        self.fields['target_value'].choices = tc
        
        
    
class MappingMeta(forms.Form):
    """
    form to define the metadata for a mapping
    pne the source, target and value maps are defined
    """
    isoformat = "%Y-%m-%dT%H:%M:%S.%f"
    invertible = forms.BooleanField(widget=forms.NullBooleanSelect,
                                    required=False)
    ## i cannot believe that an answer of false to this
    ## type hits the 'required validatio step!!!
    mapping = forms.CharField(max_length=200, required=False,
                              widget=forms.TextInput(attrs={'readonly':True}))
    last_edit = forms.CharField(max_length=50, required=False,
                                widget=forms.TextInput(attrs={'readonly':True}))
    last_editor = forms.CharField(max_length=50, required=False,
                                  widget=forms.TextInput(
                                      attrs={'readonly':True}))
    editor = forms.ChoiceField([(r['s'],r['s'].split('/')[-1]) for
                                r in moq.get_contacts(fuseki_process, 'people')]
                                , required=False)
#    editor = forms.ChoiceField([(r['s'],r['s'].split('/')[-1]) for
                                # r in moq.get_contacts('people')],
                                # widget=SelectWithPopUp)
    note = forms.CharField(max_length=200, required=False,
                           widget=forms.Textarea(attrs={'readonly':True}))
    comment = forms.CharField(max_length=200,required=False,
                              widget=forms.Textarea)
    reason = forms.CharField(max_length=50, required=False,
                             widget=forms.TextInput(attrs={'readonly':True}))
    next_reason = forms.ChoiceField(choices=[(x,x) for x in get_reasons()],
                                    required=False)
    owners = forms.CharField(max_length=200, required=False,
                             widget=forms.TextInput(attrs={'readonly':True}))
    add_owners = forms.CharField(max_length=200, required=False)
    remove_owners = forms.CharField(max_length=200, required=False)
    watchers = forms.CharField(max_length=200, required=False,
                               widget=forms.TextInput(attrs={'readonly':True}))
    add_watchers = forms.CharField(max_length=200, required=False)
    remove_watchers = forms.CharField(max_length=200, required=False)
    replaces = forms.CharField(max_length=128, required=False,
                               widget=forms.TextInput(attrs={'readonly':True}))
    status = forms.CharField(max_length=15, required=False,
                             widget=forms.TextInput(attrs={'readonly':True}))
    next_status = forms.ChoiceField(choices=[(x,x) for x in get_states()],
                                    required=False)
    source = forms.CharField(max_length=200, 
                              widget=forms.TextInput(attrs={'hidden':True}))
    target = forms.CharField(max_length=200, 
                              widget=forms.TextInput(attrs={'hidden':True}))
    valueMaps = forms.CharField(max_length=1000, required=False, 
                              widget=forms.TextInput(attrs={'hidden':True}))

    # def clean(self):
    #     print self.data['invertible']
    #     return self.cleaned_data


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


class HomeForm(forms.Form):
    """
    Form to support the home control panel
    """
    cache_status = forms.CharField(max_length=200, 
                                   widget=forms.TextInput(attrs={'size':'100',
                                                                 'readonly':True
                                                                 }))
    cache_state = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols':100,
                                                               'rows':50,
                                                               'readonly':True
                                                               }))

    def clean(self):
        if self.data.has_key('load'):
            print 'data loaded'
            fuseki_process.load()
        elif self.data.has_key('revert'):
            print 'save cache reverted'
            fuseki_process.revert()
        elif self.data.has_key('save'):
            print  'cached changes saved'
            fuseki_process.save()
        elif self.data.has_key('validate'):
            print 'validate triplestore'
            self.cleaned_data['validation'] = fuseki_process.validate()
        return self.cleaned_data


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
        self.fields['parameter'].choices = choices


class UMSTASHParam(forms.Form):
    '''A django form for adding UM STASH elements to a linkage search path
    '''
    parameter = forms.ChoiceField()
    def __init__(self,  *args, **kwargs):
        super(UMSTASHParam, self).__init__(*args, **kwargs)
        stashRes = moq.subject_by_graph(fuseki_process,
                                        'http://um/stashconcepts.ttl')
        #define choices
        choices = [(stash['subject'], stash['subject'].split('/')[-1]) for
                   stash in stashRes]
        

        self.fields['parameter'].choices = choices

class UMFCParam(forms.Form):
    '''A django form for adding UM STASH elements to a linkage search path
    '''
    parameter = forms.ChoiceField()
    def __init__(self,  *args, **kwargs):
        super(UMFCParam, self).__init__(*args, **kwargs)
        fcRs = moq.subject_by_graph(fuseki_process,
                                        'http://um/fieldcode.ttl')
        #define choices
        choices = [(fc['subject'], fc['subject'].split('/')[-1]) for fc in fcRs]
        

        self.fields['parameter'].choices = choices


class GRIBParam(forms.Form):
    '''A django form for adding GRIB elements to a linkage search path
    '''
    parameter = forms.ChoiceField()
    def __init__(self,  *args, **kwargs):
        super(GRIBParam, self).__init__(*args, **kwargs)
        gribRes = moq.subject_by_graph(fuseki_process,
                                       'http://grib/codesflags.ttl')
        #define choices
        choices = [(grib['subject'], grib['subject']) for grib in gribRes]
        
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
        snRes = moq.subject_by_graph(fuseki_process,
                                     'http://CF/cf-standard-name-table.ttl')
        #define choices
        choices = [(name['subject'],name['subject'].split('/')[-1]) for
                                                              name in snRes]

        self.fields['standard_name'].choices = choices
        self.fields['parameter'].widget = forms.HiddenInput()
        
    def clean(self):
        cleaned_data = super(CFParam, self).clean()
        pred_obj = {}
        pred_obj['mrcf:type'] = '"%s"' % cleaned_data.get('cf_type')
        if cleaned_data.get('standard_name') != \
                                        'http://cf-pcmdi.llnl.gov/documents/':
            pred_obj['mrcf:standard_name'] = '<{}>'.format(
                                             cleaned_data.get('standard_name'))
        if cleaned_data.get('long_name') != '':
            pred_obj['mrcf:long_name'] = '"%s"' % cleaned_data.get('long_name')
        if cleaned_data.get('units') != '':
            pred_obj['mrcf:units'] = '"%s"' % cleaned_data.get('units')
        # print repr(pred_obj)
        cfres = moq.get_cflinks(fuseki_process, pred_obj)
        # print 'cfres: ', cfres
        if not cfres:
            # if there is no result returned from the query, then
            # create the record and rerun the query
            cfres = moq.create_cflink(fuseki_process, pred_obj,
                                      'http://www.metarelate.net/metocean/cf')
            #cfres = moq.get_cflinks(fuseki_process, pred_obj)
        # print len(cfres)
        # print 'cfres: ', cfres
        if len(cfres) == 1:
            # assign the single result to be returned by the function
            cflink = cfres[0]['s']
        else:
            cflink = ''
        cleaned_data['parameter'] = cflink
        # print 'cflink: ',cflink
        return cleaned_data
        




class ContactForm(forms.Form):
    required_css_class = 'required'
    error_css_class = 'error'
    isoformat = ("%Y-%m-%dT%H:%M:%S.%f",)
    github_name = forms.CharField(max_length=50)
    types = (('http://www.metarelate.net/metOcean/people','people'),
             ('http://www.metarelate.net/metOcean/organisations',
                                                   'organisations'))
    register = forms.ChoiceField(choices=types)


    def clean(self):
        if READ_ONLY:
            raise ValidationError('System in Read-Only mode') 
        else:
            return self.cleaned_data




class ConceptForm(forms.Form):
    """Form for the display and selection of concepts"""
    concept = forms.CharField(max_length=200, required=False)
    components = forms.CharField(max_length=200)
    display = forms.BooleanField(required=False)
    def __init__(self, *args, **kwargs):
       super(ConceptForm, self).__init__(*args, **kwargs)
       self.fields['concept'].widget.attrs['readonly'] = True
       self.fields['components'].widget.attrs['readonly'] = True
       self.fields['concept'].widget = forms.HiddenInput()
    def clean(self):
        if self.data.has_key('create'):
            self.cleaned_data['operation'] = 'create'
            #make one
        elif self.data.has_key('search'):
            self.cleaned_data['operation'] = 'search'
        
        return self.cleaned_data


class MappingForm(forms.Form):
    """Form for the display and selection of mappings"""
    mapping = forms.CharField(max_length=200)
    source = forms.CharField(max_length=200)
    target = forms.CharField(max_length=200)
    display = forms.BooleanField(required=False)
    def __init__(self, *args, **kwargs):
       super(MappingForm, self).__init__(*args, **kwargs)
       self.fields['mapping'].widget.attrs['readonly'] = True
       self.fields['source'].widget.attrs['readonly'] = True
       self.fields['target'].widget.attrs['readonly'] = True
#       self.fields['mapping'].widget = forms.HiddenInput()

    
