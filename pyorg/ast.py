"""
Work with org file abstract syntax trees.

See https://orgmode.org/worg/dev/org-syntax.html for a description of the org
syntax.
"""

import re
from collections.abc import Iterable
from datetime import datetime
from typing import NamedTuple
from collections import ChainMap

from .util import SingleDispatchBase


_OrgNodeTypeBase = NamedTuple('OrgNodeType', [
	('name', str),
	('is_element', bool),
	('is_greater_element', bool),
	('is_recursive', bool),
	('is_object_container', bool),
])


class OrgNodeType(_OrgNodeTypeBase):
	"""The properties of an org AST node type.

	Attributes
	----------
	name : str
		The unique name of this node type.
	is_element : bool
		Whether this node type is an element. "An element defines syntactical
		parts that are at the same level as a paragraph, i.e. which cannot
		contain or be included in a paragraph."
	is_object : bool
		Whether this node type is an object. All nodes which are not elements
		are objects. "An object is a part that could be included in an element."
	is_greater_element : bool
		Whether this node type is a greater element. "Greater elements are all
		parts that can contain an element."
	is_recursive : bool
		Whether this node type is a recursive object.
	is_object_container : bool
		Whether this node type is an object container, i.e. can directly contain
		objects.

	References
	----------
	`Org Syntax <https://orgmode.org/worg/dev/org-syntax.html>`_
	"""

	@property
	def is_object(self):
		return not self.is_element

	def __repr__(self):
		return '%s(%r)' % (type(self).__name__, self.name)


#: Mapping from names of all AST node types to :class:`.OrgNodeType` instances.
ORG_NODE_TYPES = {nt.name: nt for nt in [
	#           Name                   Element Greater Recursive Container
	OrgNodeType('org-data',            True,   True,   False,    False,    ),
	OrgNodeType('babel-call',          True,   False,  False,    False,    ),
	OrgNodeType('center-block',        True,   True,   False,    False,    ),
	OrgNodeType('clock',               True,   False,  False,    False,    ),
	OrgNodeType('comment',             True,   False,  False,    False,    ),
	OrgNodeType('comment-block',       True,   False,  False,    False,    ),
	OrgNodeType('diary-sexp',          True,   False,  False,    False,    ),
	OrgNodeType('drawer',              True,   True,   False,    False,    ),
	OrgNodeType('dynamic-block',       True,   True,   False,    False,    ),
	OrgNodeType('example-block',       True,   False,  False,    False,    ),
	OrgNodeType('export-block',        True,   False,  False,    False,    ),
	OrgNodeType('fixed-width',         True,   False,  False,    False,    ),
	OrgNodeType('footnote-definition', True,   True,   False,    False,    ),
	OrgNodeType('headline',            True,   True,   False,    False,    ),
	OrgNodeType('horizontal-rule',     True,   False,  False,    False,    ),
	OrgNodeType('inlinetask',          True,   True,   False,    False,    ),
	OrgNodeType('item',                True,   True,   False,    False,    ),
	OrgNodeType('keyword',             True,   False,  False,    False,    ),
	OrgNodeType('latex-environment',   True,   False,  False,    False,    ),
	OrgNodeType('node-property',       True,   False,  False,    False,    ),
	OrgNodeType('paragraph',           True,   False,  False,    True,     ),
	OrgNodeType('plain-list',          True,   True,   False,    False,    ),
	OrgNodeType('planning',            True,   False,  False,    False,    ),
	OrgNodeType('property-drawer',     True,   True,   False,    False,    ),
	OrgNodeType('quote-block',         True,   True,   False,    False,    ),
	OrgNodeType('section',             True,   True,   False,    False,    ),
	OrgNodeType('special-block',       True,   True,   False,    False,    ),
	OrgNodeType('src-block',           True,   False,  False,    False,    ),
	OrgNodeType('table',               True,   True,   False,    False,    ),
	OrgNodeType('table-row',           True,   False,  False,    True,     ),
	OrgNodeType('verse-block',         True,   False,  False,    True,     ),
	OrgNodeType('bold',                False,  False,  True,     True,     ),
	OrgNodeType('code',                False,  False,  False,    False,    ),
	OrgNodeType('entity',              False,  False,  False,    False,    ),
	OrgNodeType('export-snippet',      False,  False,  False,    False,    ),
	OrgNodeType('footnote-reference',  False,  False,  True,     True,     ),
	OrgNodeType('inline-babel-call',   False,  False,  False,    False,    ),
	OrgNodeType('inline-src-block',    False,  False,  False,    False,    ),
	OrgNodeType('italic',              False,  False,  True,     True,     ),
	OrgNodeType('latex-fragment',      False,  False,  False,    False,    ),
	OrgNodeType('line-break',          False,  False,  False,    False,    ),
	OrgNodeType('link',                False,  False,  True,     True,     ),
	OrgNodeType('macro',               False,  False,  False,    False,    ),
	OrgNodeType('radio-target',        False,  False,  True,     True,     ),
	OrgNodeType('statistics-cookie',   False,  False,  False,    False,    ),
	OrgNodeType('strike-through',      False,  False,  True,     True,     ),
	OrgNodeType('subscript',           False,  False,  True,     True,     ),
	OrgNodeType('superscript',         False,  False,  True,     True,     ),
	OrgNodeType('table-cell',          False,  False,  True,     True,     ),
	OrgNodeType('target',              False,  False,  False,    False,    ),
	OrgNodeType('timestamp',           False,  False,  False,    False,    ),
	OrgNodeType('underline',           False,  False,  True,     True,     ),
	OrgNodeType('verbatim',            False,  False,  False,    False,    ),
]}


#: Mapping from org element/node types to their Python class
NODE_CLASSES = {}


def node_cls(type_):
	"""Register a node class for a particular type in :data:`.NODE_CLASSES`.
	"""
	def decorator(cls):
		NODE_CLASSES[type_] = cls
		return cls
	return decorator


class OrgNode:
	"""A node in an org file abstract syntax tree.

	Implements the sequence protocol as a sequence containing its child nodes
	(identically to :attr:`contents`). Also allows accessing property values by
	indexing with a string key.

	Attributes
	----------

	type: .OrgNodeType
		Node type, obtained from `org-element-type`.
	props : dict
		Dictionary of property values, obtained from `org-element-property`.
	contents : list
		List of contents (org nodes or strings), obtained from
		`org-element-contents`.
	keywords : dict
		Dictionary of keyword values.
	parent : OrgNode
		Parent AST node.
	outline : OrgOutlineNode
		Most recent outline node in the node's ancestors (not including self).
	is_outline : bool
		Whether this node is an outline node.
	"""

	is_outline = False

	def __init__(self, type_, props=None, contents=None, keywords=None, parent=None, outline=None):
		if isinstance(type_, str):
			type_ = ORG_NODE_TYPES[type_]
		if not isinstance(type_, OrgNodeType):
			raise TypeError(type(type_))
		self.type = type_

		self.props = dict(props or {})
		self.keywords = dict(keywords or {})
		self.contents = list(contents or [])
		self.parent = parent
		self.outline = outline

	@staticmethod
	def _iter_children_recursive(obj):
		"""
		Iterate through child nodes through recursive data structures (e.g.
		property values that are lists that contain nodes) but don't recurse
		into the children themselves.
		"""
		# Return nodes directly
		if isinstance(obj, OrgNode):
			yield obj

		# Skip strings - otherwise we get infinite recursion trying to iterate
		elif isinstance(obj, str):
			return

		# Iterate through lists and other collections
		elif isinstance(obj, Iterable):
			for item in obj:
				yield from OrgNode._iter_children_recursive(item)

		# Ignore

	@property
	def children(self):
		"""Iterator over all child AST nodes (in contents or keyword/property values."""
		for collection in (self.props.values(), self.keywords.values(), self.contents):
			yield from self._iter_children_recursive(collection)

	def __repr__(self):
		return '%s(type=%r)' % (type(self).__name__, self.type.name)

	def __len__(self):
		return len(self.contents)

	def __iter__(self):
		return iter(self.contents)

	def __getitem__(self, key):
		if isinstance(key, int):
			return self.contents[key]
		elif isinstance(key, str):
			return self.props[key]
		else:
			raise TypeError('Expected str or int, got %r' % type(key))

	def dump(self, index=None, indent='  ', _level=0):
		"""Print a debug representation of the node and its descendants."""
		print(indent * _level, end='')

		if index is None:
			print(self.type.name)

		else:
			print(index, self.type.name)

		for key in sorted(self.props):
			value = self.props[key]
			print('%s:%-15s = %r' % (indent * (_level + 1), key, value))

		for i, child in enumerate(self.contents):
			if isinstance(child, OrgNode):
				child.dump(i, indent=indent, _level=_level + 1)
			else:
				print('%s%d %r' % (indent * (_level + 1), i, child))


@node_cls('org-data')
@node_cls('headline')
class OrgOutlineNode(OrgNode):
	"""Org node that is a component of the outline tree.

	Corresponds to the root org-data node or a headline node.

	Attributes
	----------

	level : int
		Outline level. 0 corresponds to the root node of the file.
	title : str
		Title of outline node as plain text.
	id : str
		Unique ID for TOC tree.
	section : OrgNode
		Org node with type `"section"` that contains the outline node's direct
		content (not part of any nested outline nodes).
	"""

	is_outline = True

	def __init__(self, type_, *args, title=None, id=None, **kw):
		super().__init__(type_, *args, **kw)

		# Section and child outline nodes from content
		if self.contents and self.contents[0].type.name == 'section':
			self.section = self.contents[0]
		else:
			self.section = None


		# Default title
		if title is None:
			if self.type.name == 'headline':
				from pyorg.convert.plaintext import to_plaintext
				title = to_plaintext(self['title'], blanks=True)
			else:
				title = self.section.keywords.get('TITLE')

		self.title = title
		self.id = id

		self.level = self['level'] if self.type.name == 'headline' else 0

	@property
	def outline_children(self):
		"""Iterable over child outline nodes."""
		return (child for child in self.contents if child.is_outline)

	def outline_tree(self):
		"""Create a list of ``(child, child_tree)`` pairs."""
		return [(child, child.outline_tree()) for child in self.outline_children]

	def dump_outline(self):
		"""Print representation of node's outline subtree."""
		self._dump_outline()

	def _dump_outline(self, indent=0, n=None):
		print('  ' * indent, end='')
		if n is not None:
			print('%d. ' % n, end='')
		print(self.title)
		for (i, child) in enumerate(self.outline_children):
			child._dump_outline(indent + 1, i)


@node_cls('timestamp')
class OrgTimestampNode(OrgNode):
	"""An org node with type "timestamp".

	Attributes
	----------
	begin : datetime
		Begin date, parsed from properties
	end : datetime
		End date, parsed from properties
	"""

	def __init__(self, type_, *args, **kwargs):
		super().__init__(type_, *args, **kwargs)
		assert self.type.name == 'timestamp'

		self.begin = datetime(
			self['year-start'],
			self['month-start'],
			self['day-start'],
			self['hour-start'] or 0,
			self['minute-start'] or 0,
		)
		self.end = datetime(
			self['year-end'],
			self['month-end'],
			self['day-end'],
			self['hour-end'] or 0,
			self['minute-end'] or 0,
		)


def get_node_type(obj, name=False):
	"""Get type of AST node, returning None for other types."""
	if isinstance(obj, OrgNode):
		return obj.type.name if name else obj.type
	return None


def as_node_type(t):
	"""Convert to node type object, looking up strings by name."""
	if isinstance(t, str):
		return ORG_NODE_TYPES[t]
	if isinstance(t, OrgNodeType):
		return t
	raise TypeError(type(t))


def assign_outline_ids(root, depth=3):
	"""Assign unique IDs to outline nodes."""
	assigned = {}
	for child in root.outline_children:
		_assign_outline_ids(child, assigned, depth - 1)
	return assigned


def _assign_outline_ids(node, assigned, depth):
	id = base = re.sub(r'[^\w_-]+', '-', node.title).strip('-')
	i = 1
	while id in assigned:
		i += 1
		id = '%s-%d' % (base, i)

	node.id = id
	assigned[id] = node

	if depth > 1:
		for child in node.outline_children:
			_assign_outline_ids(child, assigned, depth - 1)


def parse_tags(string):
	"""Parse tags from string.

	Parameters
	----------
	string : str
		Tags separated by colons.

	Returns
	-------
	list[str]
		List of tags.
	"""
	string = string.strip(':')
	if not string:
		return []
	return string.split(':')


class DispatchNodeType(SingleDispatchBase):
	"""Generic function which dispatches on the node type of its first argument.
	"""

	def get_key(self, node):
		return node.type.name

	def format_key(self, key):
		return as_node_type(key).name


def dispatch_node_type(parent=None):
	"""Decorator to create DispatchNodeType instance from default implementation."""
	registry = {} if parent is None else ChainMap(parent, {})

	def decorator(default):
		return DispatchNodeType(default, registry)

	return decorator
