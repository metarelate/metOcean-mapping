
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
import json
from string import Template
import sys
import time
import urllib

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
    Helper method to return valid states.
    (consider storing these in the triple store and
    providing access via a query).
    
    """
    STATES = (
        '"Draft"',
        '"Proposed"',
        '"Approved"',
        '"Broken"',
        '"Deprecated"',
    )
    return STATES

def get_reasons():
    """
    Helper method to return valid reasons.
    (consider storing these in the triple store and
    providing access via a query).
    
    """
    REASONS = (
        '"new mapping"',
        '"added metadata"',
        '"corrected metadata"',
        '"linked to new format"',
        '"corrected links"',
        '"changed status"'
        )
    return REASONS


def formats():
    """
    Temporary, returns formats
    These should be stored in the triple store and
    provided by a query

    """
    format_choices = [('<http://metarelate.net/metocean/format/grib>', 'GRIB'),
                      ('<http://metarelate.net/metocean/format/um>', 'UM'),
                      ('<http://metarelate.net/metocean/format/cf>', 'CF')]
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
        meds = moq.get_mediators(fuseki_process, fformat)
        if isinstance(meds, list):
            meds = [(med['mediator'], med['label']) for med in meds]
        else:
            meds = (meds['mediator'], meds['label'])
        #meds = [('<http://www.metarelate.net/metocean/mediates/cf/calendar>',
        #         'calendar')]
        self.fields['mediator'].choices = meds

class NewMediator(forms.Form):
    """
    form to create a new mediator
    """
    mediator = forms.CharField()





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
    name = forms.ChoiceField(required=False)
    _name = forms.CharField(required=False)
    value = forms.CharField(required=False)
    operator = forms.CharField(required=False)
    ops = moq.subject_and_plabel(fuseki_process, 'http://openmath/tests.ttl')
    ops = [(op['subject'], op['notation']) for op in ops]
    ops = [('','')] + ops
    operator = forms.ChoiceField(required=False, choices=ops)
    
    def __init__(self, *args, **kwargs):
        self.fformat = kwargs.pop('fformat')
        super(Value, self).__init__(*args, **kwargs)
        if self.fformat == 'um':
            umRes = moq.subject_and_plabel(fuseki_process,
                                         'http://um/umdpF3.ttl')
            choices = [('','')] + [(um['subject'], um['notation']) for um in umRes]
            self.fields['name'].choices = choices
            sns = moq.subject_and_plabel(fuseki_process,
                                         'http://um/stashconcepts.ttl')
            sn_choices = [('','')]
            sn_choices += [(um['subject'], um['notation']) for um in sns]
            self.fields['stash_code'] = forms.ChoiceField(required=False,
                                                          choices=sn_choices)
            fcs = moq.subject_and_plabel(fuseki_process,
                                         'http://um/fieldcode.ttl')
            fc_choices = [('','')]
            fc_choices += [(um['subject'], um['notation']) for um in fcs]
            self.fields['field_code'] = forms.ChoiceField(required=False,
                                                          choices=fc_choices)
        elif self.fformat == 'cf':
            cfRes = moq.subject_and_plabel(fuseki_process,
                                         'http://CF/cfmodel.ttl')
            choices = [('','')] + [(cf['subject'], cf['notation']) for cf in cfRes]
            self.fields['name'].choices = choices
            sns = moq.subject_and_plabel(fuseki_process,
                                         'http://CF/cf-standard-name-table.ttl')
            sn_choices = [('','')]
            sn_choices += [(sn['subject'], sn['notation']) for sn in sns]
            self.fields['standard_name'] = forms.ChoiceField(required=False,
                                                             choices=sn_choices)
            mod = moq.subject_and_plabel(fuseki_process,
                                         'http://CF/cfmodel.ttl')
            md_choices = [('','')]
            md_choices += [(mo['subject'], mo['notation']) for mo in mod]
            print md_choices
            self.fields['cf model'] = forms.ChoiceField(required=False,
                                                        choices=md_choices)
        elif self.fformat == 'grib':
            grRes = moq.subject_and_plabel(fuseki_process,
                                           'http://grib/apikeys.ttl')
            choices = [('','')] + [(grib['subject'], grib['notation']) for grib in grRes]
            self.fields['name'].choices = choices
        else:
            raise ValueError('invalid format supplied: {}'.format(fformat))
    def clean(self):
        name = self.cleaned_data.get('name')
        _name = self.cleaned_data.get('_name')
        stcode = self.cleaned_data.get('stash_code')
        fcode = self.cleaned_data.get('field_code')
        lit = self.cleaned_data.get('value')
        st_name = self.cleaned_data.get('standard_name')
        cfmodel = self.cleaned_data.get('cf model')
        op = self.cleaned_data.get('operator')
        if name:
            if _name:
                raise forms.ValidationError('Name and name are mutually exclusive')
        else:
            if not _name:
                raise forms.ValidationError('a name must be selected')
            else:
                if self.fformat == 'cf':
                    n = '<http://def.cfconventions.org/datamodel/attribute_name#{}>'
                elif self.fformat == 'um':
                    n = '<http://reference.metoffice.gov.uk/def/um/computed_value#{}>'
                elif self.fformat == 'grib':
                    n = '<http://reference.metoffice.gov.uk/def/grib/computed_value#{}>'
                self.cleaned_data['name'] = n.format(_name) 
        if op and not (fcode or lit or stcode or st_name or cfmodel):
            raise forms.ValidationError('if operator is set '
                                        'then a value or code is '
                                        'required')
        if not op and (fcode or lit or stcode or st_name or cfmodel):
            raise forms.ValidationError('if operator is not set '
                                        'then no value or code can be '
                                        'interpreted')
        if stcode:
            if fcode or lit:
                raise forms.ValidationError('only one of value, stash code'
                                            ' or fieldcode may be entered')
            else:
                lit = stcode
        elif fcode:
            if stcode or lit:
                raise forms.ValidationError('only one of value, stash code'
                                            ' or fieldcode may be entered')
            else:
                lit = fcode
        elif st_name:
            if lit or cfmodel:
                raise forms.ValidationError('only one of value or standard_name'
                                            ' or cf model may be entered')
            else:
                lit = st_name
        elif cfmodel:
            if lit or st_name:
                raise forms.ValidationError('only one of value or standard_name'
                                            ' or cf model may be entered')
            else:
                lit = cfmodel
        try:
            float(lit)
        except ValueError:
            if lit.startswith('http'):
                lit = '<{}>'.format(lit)
            elif lit.startswith('<http'):
                lit = lit
            else:
                lit = '"{}"'.format(lit)
        self.cleaned_data['value'] = lit
        return self.cleaned_data



def _unpack_values(vals):
    """
    return the entiress for the ChoiceField choices for a list of values
    available to map
    
    """
    vals = [json.loads(aVal) for aVal in vals]
    newVals = []
    for aVal in vals:
        newS = [json.dumps(aVal), '', '', '']
        if not aVal.get('mr:subject'):
            newS[1] = aVal.get('mr:hasProperty',{}).get('mr:name', '').split('/')[-1]
        else:
            newS[1] = aVal.get('mr:subject').get('mr:hasProperty',{}).get('mr:name', '').split('/')[-1]
            newS[2] = aVal.get('mr:operator', '').split('#')[-1]
            if isinstance(aVal.get('mr:object'), unicode):
                newS[3] = aVal.get('mr:object')
            else:
                newS[3] = aVal.get('mr:object', {}).get('mr:hasProperty',{})
                newS[3] = newS[3].get('mr:name', '').split('/')[-1]
        newVals.append(newS)
    choices = [(aVal[0],'{su} {op} {ob}'.format(su=aVal[1], op=aVal[2],
                                           ob=aVal[3])) for aVal in newVals]
    return choices


class ValueMap(forms.Form):
    """
    form to define a value map
    """
    source_value = forms.ChoiceField()
    target_value = forms.ChoiceField()
    def __init__(self, *args, **kwargs):
        sc_vals = kwargs.pop('sc')
        sc = _unpack_values(sc_vals)
        tc_vals = kwargs.pop('tc')
        tc = _unpack_values(tc_vals)
        super(ValueMap, self).__init__(*args, **kwargs)
        self.fields['source_value'].choices = sc
        self.fields['target_value'].choices = tc
        
class DerivedValue(forms.Form):
    """
    """        
    ops = moq.subject_and_plabel(fuseki_process, 'http://openmath/ops.ttl')
    #print ops
    ops = [('','')] + [(op['subject'], op['notation']) for op in ops]
    _operator = forms.ChoiceField(choices=ops)
    _subject = forms.ChoiceField()
    _object = forms.ChoiceField(required=False)
    _object_literal = forms.CharField(required=False)
    def __init__(self, *args, **kwargs):
        comp_vals = kwargs.pop('components')
        components = _unpack_values(comp_vals)
        super(DerivedValue, self).__init__(*args, **kwargs)
        # components = [json.loads(component) for component in components]
        # components = [(json.dumps(component),component['mr:subject']['mr:hasProperty']['mr:name']) for
        #        component in components]
        self.fields['_subject'].choices = components
        self.fields['_object'].choices = [('','')] + components
    def clean(self):
        op = self.data.get('_operator')
        obj = self.data.get('_object')
        obj_lit = self.data.get('_object_literal')
        if not (obj or obj_lit):
            err = 'an object (choice or literal) is required'
            raise forms.ValidationError(err)
        elif obj and obj_lit:
            err = 'the object and object_literal fields are mutually exclusive'
            raise forms.ValidationError(err)
        elif obj_lit:
            try:
                float(obj_lit)
            except ValueError:
                raise forms.ValidationError('object_literal must be a number')
        return self.cleaned_data
            
        
    
class MappingMeta(forms.Form):
    """
    form to define the metadata for a mapping
    pne the source, target and value maps are defined
    """
    isoformat = "%Y-%m-%dT%H:%M:%S.%f"
    #invertible = forms.BooleanField(required=False)
    invertible = forms.ChoiceField(choices=[('"True"', 'True'),
                                            ('"False"', 'False')])
    mapping = forms.CharField(max_length=200, required=False,
                              widget=forms.TextInput(attrs={'readonly':True}))
    last_edit = forms.CharField(max_length=50, required=False,
                                widget=forms.TextInput(attrs={'readonly':True}))
    last_editor = forms.CharField(max_length=50, required=False,
                                  widget=forms.TextInput(
                                      attrs={'readonly':True}))
    editor = forms.ChoiceField([(r['s'],r['prefLabel'].split('/')[-1]) for
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
    # owners = forms.CharField(max_length=200, required=False,
    #                          widget=forms.TextInput(attrs={'readonly':True}))
    # add_owners = forms.CharField(max_length=200, required=False)
    # remove_owners = forms.CharField(max_length=200, required=False)
    # watchers = forms.CharField(max_length=200, required=False,
    #                            widget=forms.TextInput(attrs={'readonly':True}))
    # add_watchers = forms.CharField(max_length=200, required=False)
    # remove_watchers = forms.CharField(max_length=200, required=False)
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
    valueMaps = forms.CharField(max_length=1000, required=False, widget=forms.TextInput(attrs={'hidden':True}))

    def clean(self):
        source = self.data.get('source')
        map_id = self.data.get('mapping')
        if source:
            src_maps = moq.multiple_mappings(fuseki_process, source)
            if len(src_maps) > 1:
                e = 'mappings already exist for this source'
                raise forms.ValidationError(e)
        if map_id:
            mapping = moq.get_mapping_by_id(fuseki_process, map_id)
            if not mapping:
                raise forms.ValidationError('the mapping Id is not valid')
            changed = False
            changes = []
            change_keys = [('source','source'), ('target','target'),
                           ('invertible','invertible'), ('status','status'),
                           ('replaces', 'replaces'), ('comment','note'),
                           ('next_reason', 'reason'), ('editor', 'creator'),
                           ('valueMaps', 'valueMaps')]
            for fkey, mkey in change_keys:
                if self.data.get(fkey) != mapping.get(mkey, ''):
                    changed = True
                    changes.append((mkey,(self.data.get(fkey),
                                          mapping.get(mkey, ''))))
            if changed == False:
                raise forms.ValidationError('No update: mapping not changed')
            else:
                print 'changes:', changes
        return self.cleaned_data
        # if False:
        #     return self.cleaned_Data
        # else:
        #     raise forms.ValidationError('well, I would have returned')
        

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
                                   widget=forms.TextInput(attrs={'size': '100',
                                                                 'readonly':True
                                                                 }))
    cache_state = forms.CharField(required=False,
                                  widget=forms.Textarea(attrs={'cols': 100,
                                                               'rows': 50,
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


# class SearchParam(forms.Form):
#     '''
#     '''
#     parameter = forms.ChoiceField()
#     def __init__(self,  *args, **kwargs):
#         super(SearchParam, self).__init__(*args, **kwargs)
#         choices = (('', ''),
#                    ('http://i.am.a/avocet', 'avocet'),
#                    ('http://i.am.a/beaver', 'beaver'),
#                    ('http://i.am.a/cheetah', 'cheetah'),
#                    ('http://i.am.a/dugong', 'dugong'),
#                    ('http://i.am.a/emu', 'emu'))
#         self.fields['parameter'].choices = choices


# class UMSTASHParam(forms.Form):
#     """
#     A django form for adding UM STASH elements to a linkage search path
#     """
#     parameter = forms.ChoiceField()
#     def __init__(self,  *args, **kwargs):
#         super(UMSTASHParam, self).__init__(*args, **kwargs)
#         stashRes = moq.subject_by_graph(fuseki_process,
#                                         'http://um/stashconcepts.ttl')
#         # define choices
#         choices = [(stash['subject'], stash['subject'].split('/')[-1]) for
#                    stash in stashRes]
        

#         self.fields['parameter'].choices = choices

# class UMFCParam(forms.Form):
#     '''A django form for adding UM STASH elements to a linkage search path
#     '''
#     parameter = forms.ChoiceField()
#     def __init__(self,  *args, **kwargs):
#         super(UMFCParam, self).__init__(*args, **kwargs)
#         fcRs = moq.subject_by_graph(fuseki_process,
#                                         'http://um/fieldcode.ttl')
#         # define choices
#         choices = [(fc['subject'], fc['subject'].split('/')[-1]) for fc in fcRs]
        

#         self.fields['parameter'].choices = choices


# class GRIBParam(forms.Form):
#     '''A django form for adding GRIB elements to a linkage search path
#     '''
#     parameter = forms.ChoiceField()
#     def __init__(self,  *args, **kwargs):
#         super(GRIBParam, self).__init__(*args, **kwargs)
#         gribRes = moq.subject_by_graph(fuseki_process,
#                                        'http://grib/codesflags.ttl')
#         # define choices
#         choices = [(grib['subject'], grib['subject']) for grib in gribRes]
        
#         self.fields['parameter'].choices = choices

            
# class CFParam(forms.Form):
#     '''A django form for adding CF elements to a linkage search path
#     '''
#     parameter = forms.CharField(max_length=100, required=False)
#     cf_type = forms.ChoiceField(choices=[('Field','Field')], required=False)
#     standard_name = forms.ChoiceField(required=False)
#     long_name = forms.CharField(max_length=50, required=False)
#     units = forms.CharField(max_length=16, required=False)
    
#     def __init__(self,  *args, **kwargs):
#         super(CFParam, self).__init__(*args, **kwargs)
#         snRes = moq.subject_by_graph(fuseki_process,
#                                      'http://CF/cf-standard-name-table.ttl')
#         # define choices
#         choices = [(name['subject'],name['subject'].split('/')[-1]) for
#                                                               name in snRes]

#         self.fields['standard_name'].choices = choices
#         self.fields['parameter'].widget = forms.HiddenInput()
        
#     def clean(self):
#         cleaned_data = super(CFParam, self).clean()
#         pred_obj = {}
#         pred_obj['mrcf:type'] = '"%s"' % cleaned_data.get('cf_type')
#         if cleaned_data.get('standard_name') != \
#                                         'http://cf-pcmdi.llnl.gov/documents/':
#             pred_obj['mrcf:standard_name'] = '<{}>'.format(
#                                              cleaned_data.get('standard_name'))
#         if cleaned_data.get('long_name') != '':
#             pred_obj['mrcf:long_name'] = '"%s"' % cleaned_data.get('long_name')
#         if cleaned_data.get('units') != '':
#             pred_obj['mrcf:units'] = '"%s"' % cleaned_data.get('units')
#         # print repr(pred_obj)
#         cfres = moq.get_cflinks(fuseki_process, pred_obj)
#         # print 'cfres: ', cfres
#         if not cfres:
#             # if there is no result returned from the query, then
#             # create the record and rerun the query
#             cfres = moq.create_cflink(fuseki_process, pred_obj,
#                                       'http://www.metarelate.net/metocean/cf')
#             #cfres = moq.get_cflinks(fuseki_process, pred_obj)
#         # print len(cfres)
#         # print 'cfres: ', cfres
#         if len(cfres) == 1:
#             # assign the single result to be returned by the function
#             cflink = cfres[0]['s']
#         else:
#             cflink = ''
#         cleaned_data['parameter'] = cflink
#         # print 'cflink: ',cflink
#         return cleaned_data
        




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




# class ConceptForm(forms.Form):
#     """Form for the display and selection of concepts"""
#     concept = forms.CharField(max_length=200, required=False)
#     components = forms.CharField(max_length=200)
#     display = forms.BooleanField(required=False)
#     def __init__(self, *args, **kwargs):
#        super(ConceptForm, self).__init__(*args, **kwargs)
#        self.fields['concept'].widget.attrs['readonly'] = True
#        self.fields['components'].widget.attrs['readonly'] = True
#        self.fields['concept'].widget = forms.HiddenInput()
#     def clean(self):
#         if self.data.has_key('create'):
#             self.cleaned_data['operation'] = 'create'
#             #make one
#         elif self.data.has_key('search'):
#             self.cleaned_data['operation'] = 'search'
        
#         return self.cleaned_data


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

    
