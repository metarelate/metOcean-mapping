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

from collections import Iterable, MutableMapping, namedtuple
import os
from urlparse import urlparse

import pydot

from metocean.config import update


site_config = {
    'root_dir': os.path.abspath(os.path.dirname(__file__)),
    'test_dir': os.path.join(os.path.abspath(os.path.dirname(__file__)),
                             'tests'),
    'fuseki_dataset': '/metocean',
    'graph': 'metarelate.net',
}

update(site_config)


class _ComponentMixin(object):
    """
    Mixin class for common mapping component behaviour.

    """
    def __setitem__(self, key, value):
        self._immutable_exception()

    def __delitem__(self, key):
        self._immutable_exception()

    def __getattr__(self, name):
        return self.__getitem__(name)

    def __setattr__(self, name, value):
        self._immutable_exception()

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def _immutable_exception(self):
        msg = '{!r} object is immutable.'
        raise TypeError(msg.format(type(self).__name__))


class _DotMixin(object):
    """
    Mixin class for common Dot functionality.

    """
    def dot_escape(self, label):
        """
        Pre-process the string suitable for Dot notation.

        Args:
        * label:
            The string label to be escaped.

        Returns:
            String.

        """
        def escape(label, symbol):
            result = []
            for text in label.split(symbol):
                if len(text) == 0:
                    text = '\%s' % symbol
                result.append(text)
            return ''.join(result)
        for symbol in ['<', '>', ':']:
            label = escape(label, symbol)
        return label


class Mapping(_DotMixin, namedtuple('Mapping', 'uri source target')):
    """
    Represents an immutable mapping relationship between a source
    :class:`Concept` and a target :class:`Concept`.

    """
    def __new__(cls, uri, source, target):
        uri = Item(uri)
        if not isinstance(source, Concept):
            msg = 'Expected source {!r} object, got {!r}.'
            raise TypeError(msg.format(Concept.__name__,
                                       type(source).__name__))
        if not isinstance(target, Concept):
            msg = 'Expected target {!r} object, got {!r}.'
            raise TypeError(msg.format(Concept.__name__,
                                       type(target).__name__))
        return super(Mapping, cls).__new__(cls, uri, source, target)

    def __eq__(self, other):
        result = NotImplemented
        if isinstance(other, Mapping):
            result = self.uri == other.uri and \
                self.source == other.source and \
                self.target == other.target
        return result

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is not NotImplemented:
            result = not result
        return result

    def dot(self):
        """
        Generate a Dot digraph representation of this mapping.

        Returns:
            The :class:`pydot.Dot` instance.

        """
        graph = pydot.Dot(graph_type='digraph',
                          label='MetOcean',
                          labelloc='t', labeljust='l',
                          fontsize=15)
        label = self.dot_escape(self.uri.data)
        node = pydot.Node(label, label='Mapping',
                          shape='box', peripheries='2',
                          style='filled',
                          colorscheme='dark28', fillcolor='1',
                          fontsize=8)
        node.uri = self.uri.data
        graph.add_node(node)
        sgraph = pydot.Cluster('Source', label='Source Concept',
                               labelloc='b',
                               style='filled', color='lightgrey')
        snode = self.source.dot(sgraph, node)
        edge = pydot.Edge(node, snode,
                          label='Concept', fontsize=7,
                          tailport='s', headport='n')
        graph.add_edge(edge)
        graph.add_subgraph(sgraph)
        tgraph = pydot.Cluster('Target', label='Target Concept',
                               labelloc='b',
                               style='filled', color='lightgrey')
        tnode = self.target.dot(tgraph, node)
        edge = pydot.Edge(node, tnode,
                          label='Concept', fontsize=7,
                          tailport='s', headport='n')
        graph.add_edge(edge)
        graph.add_subgraph(tgraph)
        return graph

    def json_referrer(self):
        """
        return the data contents of the mapping instance ready for encoding
        as a json string

        """
        referrer = {'mapping': self.uri.data, 'mr:hasValueMap': []}
        referrer['mr:source'] = self.source.json_referrer()
        referrer['mr:target'] = self.target.json_referrer()
        return referrer


class Component(_ComponentMixin, _DotMixin, MutableMapping):
    """
    A component participates in a :class:`Property` hierarchy
    represented by its parent :class:`Concept`. It is immutable and contains
    one or more :class`Component` or :class:`PropertyComponent` members.

    A component is deemed as either *simple* or *compound*:

     * A component is *simple* iff it contains exactly one member,
       which is a :class:`PropertyComponent`.
     * A component is *compound* iff:
       * It is not *simple*, or
       * It contains two or more members.

    If a component is *simple* then each :class:`Property` that participates
    in its underlying hierarchy may be accessed via the :class:`Property`
    *name* attribute for convenience i.e. *property = component.standard_name*,
    or indexed via the associated :class:`Property` *name*
    i.e. *concept['standard_name']*.

    If a concept is *compound* then each component member is accessed by
    indexing i.e. *component = concept[0]*

    """
    def __init__(self, uri, components):
        self.__dict__['uri'] = Item(uri)
        if isinstance(components, Component) or \
                isinstance(components, PropertyComponent) or \
                not isinstance(components, Iterable):
            components = [components]
        if not len(components):
            msg = '{!r} object must contain at least one component.'
            raise ValueError(msg.format(type(self).__name__))
        temp = []
        for comp in components:
            if not isinstance(comp, (Component, PropertyComponent)):
                msg = 'Expected a {!r} or {!r} object, got {!r}.'
                raise TypeError(msg.format(Component.__name__,
                                           PropertyComponent.__name__,
                                           type(comp).__name__))
            temp.append(comp)
        self.__dict__['_data'] = tuple(sorted(temp, key=lambda c: c.uri.data))
        self.__dict__['components'] = self._data

    def __eq__(self, other):
        result = NotImplemented
        if isinstance(other, type(self)):
            result = False
            if self.uri == other.uri and len(self) == len(other):
                for i, comp in enumerate(self):
                    if comp != other[i]:
                        break
                else:
                    result = True
        return result

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is not NotImplemented:
            result = not result
        return result

    def __getitem__(self, key):
        if isinstance(key, int):
            result = self.components[key]
        else:
            if self.compound:
                self._compound_exception()
            result = None
            simple, = self.components
            for name in simple:
                if name == key:
                    result = simple[name]
                    break
        return result

    def __contains__(self, key):
        if self.compound:
            self._compound_exception()
        return key in self.components[0]

    def __repr__(self):
        fmt = '{cls}({self.uri!r}, {components!r})'
        components = self.components
        if len(components) == 1:
            components, = components
        return fmt.format(self=self, cls=type(self).__name__,
                          components=components)

    def _compound_exception(self):
        msg = '{!r} object is compound.'
        raise TypeError(msg.format(type(self).__name__))

    @property
    def simple(self):
        return len(self) == 1 and \
            isinstance(self.components[0], PropertyComponent)

    @property
    def compound(self):
        return not self.simple

    def dot(self, graph, parent, name=None):
        """
        Generate a Dot digraph representation of this mapping component.

        Args:
        * graph:
            The containing Dot graph.
        * parent:
            The parent Dot node of this property.

        Kwargs:
        * name:
            Name of the relationship between the nodes.

        """
        label = self.dot_escape('{}_{}'.format(parent.uri, self.uri.data))
        node = pydot.Node(label, label='Component',
                          style='filled', peripheries='2',
                          colorscheme='dark28', fillcolor='3',
                          fontsize=8)
        node.uri = self.uri.data
        graph.add_node(node)
        edge = pydot.Edge(parent, node,
                          tailport='s', headport='n')
        if name is not None:
            edge.set_label(self.dot_escape(name))
            edge.set_fontsize(7)
        graph.add_edge(edge)
        for comp in self.components:
            comp.dot(graph, node, 'Component')


class Concept(Component):
    """
    A concept is the root component in a :class:`Property` hierarchy,
    which defines the *domain* or *range* of a particular :class:`Mapping`
    relationship.

    A concept represents a specific :data:`scheme` or format such
    as *UM* or *CF*. It is immutable and contains one or more
    :class:`Component` or :class:`PropertyComponent` members.

    A concept is deemed as either *simple* or *compound*:

     * A concept is *simple* iff it contains exactly one member,
       which is a :class:`PropertyComponent`.
     * A concept is *compound* iff:
       * It is not *simple*, or
       * It contains two or more members.

    If a concept is *simple* then each :class:`Property` that participates
    in its hierarchy may be accessed via the :class:`Property` *name* attribute
    for convenience i.e. *property = concept.standard_name*, or indexed via
    the associated :class:`Property` *name* i.e. *concept['standard_name']*.

    If a concept is *compound* then each component member is accessed via
    indexing i.e. *component = concept[0]*

    """
    def __init__(self, uri, scheme, components):
        super(Concept, self).__init__(uri, components)
        self.__dict__['scheme'] = Item(scheme)

    def __eq__(self, other):
        result = NotImplemented
        if isinstance(other, Concept):
            result = False
            if self.scheme == other.scheme:
                result = super(Concept, self).__eq__(other)
        return result

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is not NotImplemented:
            result = not result
        return result

    def __repr__(self):
        fmt = '{cls}({self.uri!r}, {self.scheme!r}, {components!r})'
        components = self.components
        if len(components) == 1:
            components, = components
        return fmt.format(self=self, cls=type(self).__name__,
                          components=components)

    def dot(self, graph, parent, name=None):
        """
        Generate a Dot digraph representation of this mapping concept.

        Args:
        * graph:
            The containing Dot graph.
        * parent:
            The parent Dot node of this property.

        Kwargs:
        * name:
            Name of the relationship between the nodes.

        """
        label = self.dot_escape('{}_{}'.format(parent.uri, self.uri.data))
        node = pydot.Node(label, label=self.scheme.dot(),
                          shape='box', style='filled',
                          colorscheme='dark28', fillcolor='2',
                          fontsize=8)
        node.uri = self.uri.data
        graph.add_node(node)
        for comp in self.components:
            comp.dot(graph, node, 'Component')
        return node

    def json_referrer(self):
        """
        return the data contents of the component instance ready for encoding
        as a json string

        """
        if len(self) == 1 and self.uri.data == self.components[0].uri.data:
            prop_ref = self.components[0].json_referrer()
            prop_ref['mr:hasFormat'] = self.scheme.data
            referrer = prop_ref
        else:
            referrer = {'component': self.uri.data,
                        'mr:hasFormat': self.scheme.data,
                        'mr:hasComponent': []}
            for comp in self.components:
                prop_ref = comp.json_referrer()
                prop_ref['mr:hasFormat'] = self.scheme.data
                referrer['mr:hasComponent'].append(prop_ref)
        return referrer


class PropertyComponent(_ComponentMixin, _DotMixin, MutableMapping):
    """
    A property component must be contained within a parent
    :class:`Concept` or :class:`Component`. It is immutable and
    contains one or more uniquely named :class:`Property` members.

    The property component provides dictionary style access to its
    :class:`Property` members, keyed on the :data:`Property.name`.
    Alternatively, attribute access via the member *name* is supported
    as a convenience.

    Note that, each :class:`Property` member must have a unique *name*.

    A property component is deemed as either *simple* or *compound*:

     * A property component is *simple* iff all its :class:`Property`
       members are *simple*.
     * A property component is *compound* iff it contains at least
       one :class:`Property` member that is *compound*.

    """
    def __init__(self, uri, properties):
        self.__dict__['uri'] = Item(uri)
        self.__dict__['_data'] = {}
        if isinstance(properties, Property) or \
                not isinstance(properties, Iterable):
            properties = [properties]
        if not len(properties):
            msg = '{!r} object must contain at least one {!r}.'
            raise ValueError(msg.format(type(self).__name__,
                                        Property.__name__))
        for prop in properties:
            if not isinstance(prop, Property):
                msg = 'Expected a {!r} object, got {!r}.'
                raise TypeError(msg.format(Property.__name__,
                                           type(prop).__name__))
            self.__dict__['_data'][prop.name] = prop

    def __eq__(self, other):
        result = NotImplemented
        if isinstance(other, PropertyComponent):
            result = False
            if self.uri == other.uri and set(self.keys()) == set(other.keys()):
                for key in self.keys():
                    if self[key] != other[key]:
                        break
                else:
                    result = True
        return result

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is not NotImplemented:
            result = not result
        return result

    def __getitem__(self, key):
        result = None
        for item in self._data.iterkeys():
            if item == key:
                result = self._data[item]
                break
        return result

    def __contains__(self, key):
        result = False
        if isinstance(key, (Item, basestring)):
            result = self[key] is not None
        elif isinstance(key, Property):
            result = key == self[key.name]
        return result

    def __repr__(self):
        fmt = '{cls}({self.uri!r}, {properties!r})'
        properties = sorted(self._data.values())
        if len(properties) == 1:
            properties, = properties
        return fmt.format(self=self, cls=type(self).__name__,
                          properties=properties)

    @property
    def simple(self):
        return all([prop.simple for prop in self.itervalues()])

    @property
    def compound(self):
        return not self.simple

    def dot(self, graph, parent, name=None):
        """
        Generate a Dot digraph representation of this mapping component.

        Args:
        * graph:
            The containing Dot graph.
        * parent:
            The parent Dot node of this componet.

        Kwargs:
        * name:
            Name of the relationship between the nodes.

        """
        if parent.uri == self.uri.data:
            # This component references one or more properties.
            for prop in self.values():
                prop.dot(graph, parent, 'Property')
        else:
            # This component references another component.
            label = self.dot_escape('{}_{}'.format(parent.uri, self.uri.data))
            node = pydot.Node(label, label='Component',
                              style='filled', peripheries='2',
                              colorscheme='dark28', fillcolor='3',
                              fontsize=8)
            node.uri = self.uri.data
            graph.add_node(node)
            edge = pydot.Edge(parent, node,
                              tailport='s', headport='n')
            if name is not None:
                edge.set_label(self.dot_escape(name))
                edge.set_fontsize(7)
            graph.add_edge(edge)
            for prop in self.values():
                prop.dot(graph, node, 'Property')

    def json_referrer(self):
        """
        return the data contents of the propertyComponent instance
        ready for encoding as a json string

        """
        referrer = {'component': self.uri.data,
                    'mr:hasProperty': []}
        for item in self.itervalues():
            referrer['mr:hasProperty'].append(item.json_referrer())
        return referrer


class Property(_DotMixin, namedtuple('Property', 'uri name value operator')):
    """
    Represents a named tuple property participating in a :class:`Mapping`
    relationship.

    A property is immutable and must have a *name*, but it may also have
    additional meta-data representing its associated *value* and *operator*
    i.e. *standard_name = air_temperature*, where *name* is "standard_name",
    *operator* is "=". and *value* is "air_temperature".

    A :class:`Property` member that participated in a :class:`Mapping`
    relationship must be contained within a :class:`PropertyComponent`.

    A property is deemed as either *simple* or *compound*:

     * A property is *simple* iff its *value* references a :class:`Item`.
     * A property is *compound* iff its *value* references a
       :class:`PropertyComponent`.

    """
    def __new__(cls, uri, name, value=None, operator=None):
        new_uri = Item(uri)
        new_name = Item(name)
        if (value is None and operator is not None) or \
                (value is not None and operator is None):
            msg = 'The {!r} and {!r} of a {!r} must be both set or unset.'
            raise ValueError(msg.format('value', 'operator', cls.__name__))
        new_value = None
        new_operator = None
        if value is not None:
            if isinstance(value, (Item, basestring)):
                new_value = Item(value)
            elif isinstance(value, PropertyComponent):
                new_value = value
            else:
                msg = 'Invalid {!r} value, got {!r}.'
                raise TypeError(msg.format(cls.__name__,
                                           type(value).__name__))
        if operator is not None:
            new_operator = Item(operator)
        return super(Property, cls).__new__(cls, new_uri, new_name,
                                            new_value, new_operator)

    def __eq__(self, other):
        result = NotImplemented
        if isinstance(other, Property):
            result = self.uri == other.uri and \
                self.name == other.name and \
                self.value == other.value and \
                self.operator == other.operator
        elif self.simple and isinstance(other, (Item, basestring)):
            result = self.value == other
        return result

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is not NotImplemented:
            result = not result
        return result

    def __setattr__(self, name, value):
        msg = '{!r} instance is immutable.'
        raise TypeError(msg.format(type(self).__name__))

    def __repr__(self):
        fmt = '{cls}(uri={self.uri!r}, name={self.name!r}{value}{operator})'
        value = operator = component = ''
        if self.value is not None:
            value = ', value={!r}'.format(self.value)
        if self.operator is not None:
            operator = ', operator={!r}'.format(self.operator)
        return fmt.format(self=self, cls=type(self).__name__,
                          value=value, operator=operator)

    @property
    def simple(self):
        return isinstance(self.value, Item) or self.value is None

    @property
    def compound(self):
        return not self.simple

    @property
    def complete(self):
        return self.simple and self.value is not None and self.value.complete

    def dot(self, graph, parent, name=None):
        """
        Generate a Dot digraph representation of this mapping property.

        Args:
        * graph:
            The containing Dot graph.
        * parent:
            The parent Dot node of this property.

        Kwargs:
        * name:
            Name of the relationship between the nodes.

        """
        items = []
        items.append(self.name.dot())
        if self.operator is not None:
            items.append(self.operator.dot())
        if self.value is not None and isinstance(self.value, Item):
            items.append(self.value.dot())
        items = ' '.join(items)
        label = self.dot_escape('{}_{}'.format(parent.uri, self.uri.data))
        node = pydot.Node(label, label=items,
                          style='filled',
                          colorscheme='dark28', fillcolor='4',
                          fontsize=8)
        node.uri = self.uri.data
        graph.add_node(node)
        edge = pydot.Edge(parent, node,
                          tailport='s', headport='n')
        if name is not None:
            edge.set_label(self.dot_escape(name))
            edge.set_fontsize(7)
        graph.add_edge(edge)

        if self.value is not None and not isinstance(self.value, Item):
            # This property references a component.
            self.value.dot(graph, node, 'Component')

    def json_referrer(self):
        """
        return the data contents of the property instance ready for encoding
        as a json string

        """
        referrer = {}
        referrer['property'] = self.uri.data
        referrer['mr:name'] = self.name.data
        if self.operator:
            referrer['mr:operator'] = self.operator.data
        if self.value:
            if self.simple:
                referrer['rdf:value'] = self.value.data
            else:
                referrer['mr:hasComponent'] = self.value.json_referrer()
        return referrer


class Item(_DotMixin, namedtuple('Item', 'data notation')):
    """
    Represents a mapping data item and associated skos notation in
    the form of an immutable named tuple.

    """
    def __new__(cls, data, notation=None):
        new_data = data
        new_notation = None
        if isinstance(data, Item):
            new_data = data.data
            new_notation = data.notation
        if notation is not None:
            if isinstance(notation, basestring) and len(notation) > 1 and \
                    notation.startswith('"') and notation.endswith('"'):
                notation = notation[1:-1]
            new_notation = notation
        return super(Item, cls).__new__(cls, new_data, new_notation)

    def is_uri(self):
        """
        Determine whether the mapping data item is a valid URI.

        Returns:
            Boolean.

        """
        result = False
        if isinstance(self.data, basestring):
            uri = self.data
            if uri.startswith('<') and uri.endswith('>'):
                uri = uri[1:-1]
            uri = urlparse(uri)
            result = len(uri.scheme) > 0 and len(uri.netloc) > 0
        return result

    def __eq__(self, other):
        result = NotImplemented
        if isinstance(other, Item):
            result = self.data == other.data and \
                self.notation == other.notation
        elif isinstance(other, basestring):
            notation = self.notation
            if isinstance(notation, basestring):
                notation = notation.lower()
            result = self.data == other or notation == other.lower()
        return result

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is not NotImplemented:
            result = not result
        return result

    def __setattr__(self, name, value):
        msg = '{!r} instance is immutable.'
        raise TypeError(msg.format(type(self).__name__))

    def __repr__(self):
        fmt = '{self.data!r}'
        if self.notation is not None:
            fmt = '{cls}(data={self.data!r}, notation={self.notation!r})'
        return fmt.format(self=self, cls=type(self).__name__)

    @property
    def complete(self):
        return self.data is not None and self.notation is not None

    def dot(self):
        """
        Return a Dot escaped string representation of the mapping item.

        If the skos notation is available, this has priority.

        Returns:
            String.

        """
        label = self.dot_escape(self.data)
        if self.notation is not None:
            label = self.dot_escape(str(self.notation))
        return label
