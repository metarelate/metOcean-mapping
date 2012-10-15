
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
import time
import sys

import metocean.prefixes as prefixes

from settings import READ_ONLY
from django import forms
from string import Template
from django.utils.safestring import mark_safe
from django.utils import formats
from django.core.urlresolvers import reverse

import metocean.queries as moq


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
                kwargs={'hashval' : value}), "go to previous")
        return mark_safe(tpl)

    def clean(self):
        return self.cleaned_data

class BulkLoadForm(forms.Form):
    file = forms.FileField(
        label = 'Select a CSV file to upload',
        help_text = 'maximum size 2MB',
        required=False) 

class RecordForm(forms.Form):
    # class Meta:
    #     model = BaseRecord
    #     exclude = ('baserecordMD5',)

    def __init__(self, *args, **kwargs):
        super(RecordForm, self).__init__(*args, **kwargs)
        self.fields['current_status'] = forms.CharField(max_length=15)
        if self.initial.has_key('metadata_element'):
            self.fields['metadata_element'].widget.attrs['readonly'] = True
            #self.fields['metadata_element'].widget.attrs['disabled'] = "disabled"
        if READ_ONLY:
            for fieldname in self.fields:
                self.fields[fieldname].widget.attrs['readonly'] = True
                self.fields[fieldname].widget.attrs['disabled'] = 'disabled'

    def clean(self):
        if READ_ONLY:
            raise ValidationError('System in Read-Only mode') 
        else:
            return self.cleaned_data

    

class MappingEditForm(forms.Form):
    required_css_class = 'required'
    error_css_class = 'error'
    isoformat = ("%Y-%m-%dT%H:%M:%S.%f",)
    mapping = forms.URLField()
    linkage = forms.URLField()
    last_edit = forms.CharField(max_length=50)
    last_editor = forms.CharField(max_length=50)
    editor = forms.CharField(max_length=50, required=False)
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
    previous = forms.CharField(max_length=32)
    current_status = forms.CharField(max_length=15)
    next_status = forms.ChoiceField(choices=[(x,x) for x in get_states()])
    cflinks = forms.CharField(max_length=1000, required=False)
    umlinks = forms.CharField(max_length=1000, required=False)
    griblinks  = forms.CharField(max_length=1000, required=False)

    def __init__(self, *args, **kwargs):
        super(MappingEditForm, self).__init__(*args, **kwargs)
        pre = prefixes.Prefixes()
        self.fields['current_status'].widget.attrs['readonly'] = True
        self.fields['owners'].widget.attrs['readonly'] = True
        self.fields['watchers'].widget.attrs['readonly'] = True
        self.fields['last_edit'].widget.attrs['readonly'] = True
        self.fields['last_editor'].widget.attrs['readonly'] = True
        self.fields['last_comment'].widget.attrs['readonly'] = True
        self.fields['last_reason'].widget.attrs['readonly'] = True
        self.fields['last_edit'].required = False
        self.fields['previous'].widget = URLwidget()
        self.fields['previous'].required = False
        self.fields['mapping'].widget.attrs['readonly'] = True
        self.fields['linkage'].widget = forms.HiddenInput()
        self.fields['cflinks'].widget = forms.HiddenInput()
        self.fields['umlinks'].widget = forms.HiddenInput()
        self.fields['griblinks'].widget = forms.HiddenInput()
        if kwargs.has_key('initial'):
            cflinks = None
            if kwargs['initial'].has_key('cflinks'):
                cflinks = kwargs['initial']['cflinks']
            if cflinks:
                for i, cflink in enumerate(cflinks.split('&')):
                    for k,v in moq.get_cflink_by_id(cflink)[0].iteritems():
                        self.fields['cflink%i_%s' % (i,k)] = forms.URLField(initial=v)
                        self.fields['cflink%i_%s' % (i,k)].widget.attrs['readonly'] = True
            umlinks = None
            if kwargs['initial'].has_key('umlinks'):
                umlinks = kwargs['initial']['umlinks']
            if umlinks:
                for i, umlink in enumerate(umlinks.split('&')):
                    self.fields['umlink%i' % i] = forms.URLField(initial=umlink)
                    self.fields['umlink%i' % i].widget.attrs['readonly'] = True
            griblinks = None
            if kwargs['initial'].has_key('cflinks'):
                griblinks = kwargs['initial']['griblinks']
            if griblinks:
                for i, griblink in enumerate(griblinks.split('&')):
                    self.fields['griblink%i' % i] = forms.URLField(initial=griblink)
                    self.fields['griblink%i' % i].widget.attrs['readonly'] = True


    def clean(self):
        if READ_ONLY:
            raise ValidationError('System in Read-Only mode') 
        else:
            return self.cleaned_data

    def clean_last_edit(self):
        data = self.cleaned_data.get('last_edit')
        for format in self.isoformat:
            try:
                return str(datetime.datetime(*time.strptime(str(data), format)[:6]))
            except ValueError:
                continue
        raise forms.ValidationError("Invalid ISO DateTime format")


class MappingNewForm(MappingEditForm):
    reason = forms.CharField(max_length=15, initial='new mapping')
    next_status = forms.CharField(max_length=15, initial='Draft')

    def __init__(self, *args, **kwargs):
        super(MappingNewForm, self).__init__(*args, **kwargs)
        self.fields['last_edit'].widget = forms.HiddenInput()
        self.fields['last_editor'].widget = forms.HiddenInput()
        self.fields['last_comment'].widget = forms.HiddenInput()
        self.fields['last_reason'].widget = forms.HiddenInput()
        self.fields['owners'].widget = forms.HiddenInput()
        self.fields['remove_owners'].widget = forms.HiddenInput()
        self.fields['watchers'].widget = forms.HiddenInput()
        self.fields['remove_watchers'].widget = forms.HiddenInput()
        self.fields['current_status'].widget = forms.HiddenInput()
        self.fields['reason'].widget.attrs['readonly'] = True
        self.fields['next_status'].widget.attrs['readonly'] = True
        
        

