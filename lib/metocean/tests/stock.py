# (C) British Crown Copyright 2013, Met Office
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

"""
A collection of routines that create standard metOcean mappings for
test purposes.

"""

import metocean


def property_cf_standard_name():
    data = '<http://def.cfconventions.org/datamodel/standard_name>'
    notation = 'standard_name'
    name = metocean.Item(data, notation)

    data = '<http://def.cfconventions.org/standard_names/' \
        'tendency_of_sea_ice_thickness_due_to_dynamics>'
    notation = 'tendency_of_sea_ice_thickness_due_to_dynamics'
    value = metocean.Item(data, notation)

    data = '<http://www.openmath.org/cd/relation1.xhtml#eq>'
    notation = '='
    operator = metocean.Item(data, notation)

    uri = '<http://www.metarelate.net/metOcean/property/test_p001'
    return metocean.Property(uri, name, value, operator)


def property_cf_type():
    data = '<http://def.cfconventions.org/datamodel/type>'
    notation = 'type'
    name = metocean.Item(data, notation)

    data = '<http://def.cfconventions.org/datamodel/Field>'
    notation = 'Field'
    value = metocean.Item(data, notation)

    data = '<http://www.openmath.org/cd/relation1.xhtml#eq>'
    notation = '='
    operator = metocean.Item(data, notation)

    uri = '<http://www.metarelate.net/metOcean/property/test_p002>'
    return metocean.Property(uri, name, value, operator)


def property_cf_units():
    data = '<http://def.cfconventions.org/datamodel/units>'
    notation = 'units'
    name = metocean.Item(data, notation)

    value = metocean.Item(data='"m s-1"', notation='m s-1')

    data = '<http://www.openmath.org/cd/relation1.xhtml#eq>'
    notation = '='
    operator = metocean.Item(data, notation)

    uri = '<http://www.metarelate.net/metOcean/property/test_p003>'
    return metocean.Property(uri, name, value, operator)


def property_um_stash():
    data = '<http://reference.metoffice.gov.uk/def/um/umdp/F3/stash>'
    notation = 'stash'
    name = metocean.Item(data, notation)

    data = '<http://reference.metoffice.gov.uk/def/um/stash/concept/' \
        'm02s32i202>'
    notation = 'm02s32i202'
    value = metocean.Item(data, notation)

    data = '<http://www.openmath.org/cd/relation1.xhtml#eq>'
    notation = '='
    operator = metocean.Item(data, notation)

    uri = '<http://www.metarelate.net/metOcean/property/test_p004>'
    return metocean.Property(uri, name, value, operator)


def property_component_cf():
    properties = [property_cf_standard_name(),
                  property_cf_units(),
                  property_cf_type()]
    uri = '<http://www.metarelate.net/metOcean/component/test_c001>'
    return metocean.PropertyComponent(uri, properties)


def property_component_um():
    uri = '<http://www.metarelate.net/metOcean/component/test_c002>'
    return metocean.PropertyComponent(uri, property_um_stash())


def simple_component_cf():
    uri = '<http://www.metarelate.net/metOcean/component/test_c003>'
    return metocean.Component(uri, property_component_cf())


def compound_component_cf():
    uri = '<http://www.metarelate.net/metOcean/component/test_c004>'
    return metocean.Component(uri, simple_component_cf())


def simple_concept_cf():
    data = '<http://www.metarelate.net/metOcean/format/cf>'
    notation = 'cf'
    scheme = metocean.Item(data, notation)

    uri = '<http://www.metarelate.net/metOcean/component/test_c005>'
    return metocean.Concept(uri, scheme, property_component_cf())


def compound_concept_cf():
    data = '<http://www.metarelate.net/metOcean/format/cf>'
    notation = 'cf'
    scheme = metocean.Item(data, notation)

    uri = '<http://www.metarelate.net/metOcean/component/test_c006>'
    return metocean.Concept(uri, scheme, simple_component_cf())


def simple_concept_um():
    data = '<http://www.metarelate.net/metOcean/format/um>'
    notation = 'um'
    scheme = metocean.Item(data, notation)

    uri = '<http://www.metarelate.net/metOcean/component/test_c007>'
    return metocean.Concept(uri, scheme, property_component_um())


def simple_mapping_um_cf():
    uri = '<http://www.metarelate.net/metOcean/mapping/test_m001>'
    return metocean.Mapping(uri, simple_concept_um(), simple_concept_cf())
