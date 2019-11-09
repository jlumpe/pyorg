"""
Work with org file abstract syntax trees.

See https://orgmode.org/worg/dev/org-syntax.html for a description of the org
syntax.
"""

import re
from collections.abc import Iterable
from typing import NamedTuple
from collections import ChainMap
from copy import copy, deepcopy

from .util import SingleDispatchBase, parse_iso_date


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


def dump_ast(value, properties=False, indent='  ', _level=0):
	"""Print a debug representation of an org AST node and its descendants.

	Parameters
	----------
	value : .OrgNode
	properties : bool
		Also print node properties.
	indent : str
		Characters to indent with.
	"""

	if isinstance(value, OrgNode):

		print(value.type.name)

		if properties:
			for key in sorted(value.properties):
				print('%s:%-15s = ' % (indent * (_level + 1), key), end='')
				dump_ast(value.properties[key], properties, indent, _level + 1)

		for i, child in enumerate(value.contents):
			print('%s%d ' % (indent * (_level + 1), i), end='')
			dump_ast(child, properties, indent, _level + 1)

	# Special printing for secondary strings, which are lists containing more nodes
	elif isinstance(value, list) and any(isinstance(item, OrgNode) for item in value):
		print('[')
		for item in value:
			print(indent * (_level + 1), end='')
			dump_ast(item, properties, indent, _level + 1)
		print((indent * _level) + ']')

	else:
		print(repr(value))


class OrgTimestampInterval:
	"""An interval of time stored in an Org mode time stamp's repeater or warning.

	Attributes
	----------
	type : str
	unit : str
	value : float
	"""
	def __init__(self, type_, unit, value):
		self.type = type_
		self.unit = unit
		self.value = value


class OrgTimestamp:
	"""Stores Org mode timestamp data, without the whole AST node.

	Attributes
	----------
	tstype : str
	start : datetime.datetime
	end : datetime.datetime
	repeater : .OrgTimestampInterval
	warning : .OrgTimestampInterval
	"""

	def __init__(self, tstype, start, end=None, repeater=None, warning=None):
		self.tstype = tstype
		self.start = start
		self.end = start if end is None else end
		self.repeater = repeater
		self.warning = warning

	@property
	def is_range(self):
		return self.start and self.end and (self.start != self.end)

	@property
	def interval(self):
		return self.end - self.start if self.start and self.end else None

	def __repr__(self):
		if self.is_range:
			return '<%s %s %s to %s>' % (type(self).__name__, self.tstype, self.start, self.end)
		else:
			return '<%s %s %s>' % (type(self).__name__, self.tstype, self.start or self.end)


class OrgNode:
	"""A node in an org file abstract syntax tree.

	Implements the sequence protocol as a sequence containing its child nodes
	(identically to :attr:`contents`). Also allows accessing property values by
	indexing with a string key.

	Attributes
	----------

	type: .OrgNodeType
		Node type, obtained from `org-element-type`.
	properties : dict
		Dictionary of property values, obtained from `org-element-property`.
	contents : list
		List of contents (org nodes or strings), obtained from
		`org-element-contents`.
	ref : str
		A unique ID assigned to the node during the export process.
	keywords : dict
		Dictionary of keyword values.
	meta : dict
		A dictionary containing arbitrary application-specific metadata.
	is_outline : bool
		Whether this node is an outline node.
	"""

	is_outline = False

	def __init__(self, type_, properties=None, contents=None, keywords=None, ref=None, meta=None):
		if isinstance(type_, str):
			type_ = ORG_NODE_TYPES[type_]
		if not isinstance(type_, OrgNodeType):
			raise TypeError(type(type_))
		self.type = type_

		self.properties = dict(properties or {})
		self.keywords = dict(keywords or {})
		self.ref = ref
		self.contents = list(contents or [])
		self.meta = dict(meta or [])

	def __copy__(self, deep=False):
		cp = deepcopy if deep else copy
		return type(self)(
			self.type,
			properties=cp(self.properties),
			contents=cp(self.contents),
			keywords=cp(self.keywords),
			ref=self.ref,
		)

	def __deepcopy__(self):
		return self.__copy__(deep=True)

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
		for collection in (self.properties.values(), self.keywords.values(), self.contents):
			yield from self._iter_children_recursive(collection)

	def descendants(self, incself=False, properties=False):
		"""Recursively iterate over all of the node's descendants.

		Parameters
		----------
		incself : bool
			Include self.
		properties : bool
			Include children in the node's properties, not just :attr:`contents`
			(see :attr:`children`).

		Yields
		-------
		.OrgNode
		"""
		if incself:
			yield self

		for item in (self.children if properties else self.contents):
			yield from item.descendants(incself=True, properties=properties)

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
			return self.properties[key]
		else:
			raise TypeError('Expected str or int, got %r' % type(key))

	def dump(self, properties=False, indent='  '):
		"""Print a debug representation of the node and its descendants.

		Parameters
		----------
		value : .OrgNode
		properties : bool
			Also print node properties.
		indent : str
		Characters to indent with.
		"""
		dump_ast(self, properties, indent)


class OrgOutlineNode(OrgNode):
	"""Abstract base class for org node that is a component of the outline tree.

	Corresponds to the root org-data node or a headline node.

	Attributes
	----------
	level : int
		Outline level. 0 corresponds to the root node of the file.
	section : OrgNode
		Org node with type `"section"` that contains the outline node's direct
		content (not part of any nested outline nodes).
	subheadings : list
		List of nested headings.
	"""

	is_outline = True

	def __new__(cls, *args, **kwargs):
		if cls is OrgOutlineNode:
			raise TypeError("Can't instantiate abstract base class directly")
		return object.__new__(cls)

	@property
	def section(self):
		if self.contents and self.contents[0].type.name == 'section':
			return self.contents[0]
		return None

	@property
	def subheadings(self):
		if self.contents and self.contents[0].type.name == 'section':
			return self.contents[1:]
		return self.contents[:]

	def outline_tree(self):
		"""Create a list of ``(child, child_tree)`` pairs."""
		return [(child, child.outline_tree()) for child in self.subheadings]

	def dump_outline(self, depth=None, indent='  '):
		"""Print representation of node's outline subtree.

		Parameters
		----------
		depth : int
			Maximum depth to print.
		indent : str
			String to indent with.
		"""
		self._dump_outline(None, 0, depth, indent)

	def _dump_outline(self, n, depth, maxdepth, indent):
		print(indent * depth, end='')
		if n is not None:
			print('%d. ' % n, end='')
		print(self._dump_name())

		if maxdepth is None or depth < maxdepth:
			nextdepth = None if depth is None else depth + 1
			for (i, child) in enumerate(self.subheadings):
				child._dump_outline(i, nextdepth, maxdepth, indent)

	def _dump_name(self):
		"""Get the name to show for this node when dumping outline."""
		raise NotImplementedError()


@node_cls('headline')
class OrgHeadlineNode(OrgOutlineNode):
	"""Org header element.

	Attributes
	----------
	title : str
		Title of headline as plain text.
	id : str
		Unique ID for TOC tree.
	has_todo : bool
		Whether this outline has a TODO keyword.
	priority_chr : str
		Priority character if headline with priority, otherwise None.
	scheduled : OrgTimestamp
		The timestamp in the "scheduled" property of the headline, if present.
	deadline : OrgTimestamp
		The timestamp in the "deadline" property of the headline, if present.
	closed : OrgTimestamp
		The timestamp in the "closed" property of the headline, if present.
	"""

	def __init__(self, type_, *args, title=None, id=None, **kw):
		super().__init__(type_, *args, **kw)
		assert self.type.name == 'headline'

		# Default title
		if title is None:
			from pyorg.convert.plaintext import to_plaintext
			title = to_plaintext(self['title'], blanks=True)

		self.title = title
		self.id = self.ref if id is None else id
		self.level = self['level']

	@property
	def has_todo(self):
		return self['todo-type'] is not None

	@property
	def priority_chr(self):
		return None if self['priority'] is None else chr(self['priority'])

	@property
	def deadline(self):
		return self.properties.get('deadline')

	@property
	def scheduled(self):
		return self.properties.get('scheduled')

	@property
	def closed(self):
		return self.properties.get('closed')

	def _dump_name(self):
		return self.title


@node_cls('org-data')
class OrgDataNode(OrgOutlineNode):
	"""Root node for an org mode parse tree.

	Doesn't do anything special, aside from being the outline node at level 0.
	"""

	def __init__(self, type_, *args, **kw):
		super().__init__(type_, *args, **kw)
		assert self.type.name == 'org-data'

	def _dump_name(self):
		return 'Root'


@node_cls('timestamp')
class OrgTimestampNode(OrgNode, OrgTimestamp):
	"""An org node with type "timestamp"."""

	def __init__(self, type_, *args, **kwargs):
		OrgNode.__init__(self, type_, *args, **kwargs)
		assert self.type.name == 'timestamp'

		OrgTimestamp.__init__(
			self,
			self['type'],
			start=parse_iso_date(self['start']) if self.properties.get('start') else None,
			end=parse_iso_date(self['end']) if self.properties.get('end') else None,
		)


@node_cls('table')
class OrgTableNode(OrgNode):
	"""An org node with type "table".

	Attributes
	----------
	rows : list of OrgNode
		List of standard rows.
	nrows : int
		Number of (non-rule) rows in table. This includes the header.
	ncols: int
		Number of columns in table.
	"""

	def blocks(self):
		"""Standard rows divided into "blocks", which were separated by rule rows.

		Returns
		-------
		list of list of OrgNode
		"""
		current_block = []
		blocks = [current_block]

		for row in self.contents:
			assert row.type.name == 'table-row'

			if row['type'] == 'rule':
				# New block
				current_block = []
				blocks.append(current_block)

			elif row['type'] == 'standard':
				current_block.append(row.contents)

			else:
				raise ValueError()

		return blocks

	@property
	def rows(self):
		return [row for row in self.contents if row['type'] == 'standard']

	@property
	def nrows(self):
		return sum(row['type'] == 'standard' for row in self.contents)

	@property
	def ncols(self):
		return len(self.contents[0])

	def cells(self):
		return [list(row.contents) for row in self.rows]


def get_node_type(obj, name=False):
	"""Get type of AST node, returning None for other Python types."""
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


def as_secondary_string(obj):
	"""Convert argument to a "secondary string" (list of nodes or strings).

	Parameters
	----------
	obj : .OrgNode or str or list

	Returns
	-------
	list

	Raises
	------
	TypeError : if ``obj`` is not a str or :class:`.OrgNode` or iterable of these.
	"""
	if isinstance(obj, (str, OrgNode)):
		return [obj]

	ss = list(obj)
	for item in ss:
		if not isinstance(item, (str, OrgNode)):
			raise TypeError('Items must be OrgNode or str, got %r' % type(item))

	return ss


class OrgDocument:
	"""Represents an entire Org mode document.

	Attributes
	----------
	root : OrgOutlineNode
		The root of the document's Abstract Syntax Tree.
	properties : dict
		Additional file-level properties attached to the document, such as the
		author or date. Values may be strings or secondary strings.
	meta : dict
		A dictionary containing arbitrary application-specific metadata.
	"""

	def __init__(self, root, properties=None, meta=None):
		self.root = root
		self.properties = dict(properties or [])
		self.meta = dict(meta or [])

	def assign_header_ids(self, depth=3):
		"""Assign unique IDs to headers."""
		assigned = {}
		for child in self.root.subheadings:
			self._assign_header_ids(child, assigned, depth)
		return assigned

	def _assign_header_ids(self, header, assigned, depth):

		id_ = self._make_header_id(header, assigned)
		header.id = id_
		assigned[id_] = header

		if depth > 1:
			for child in header.subheadings:
				self._assign_header_ids(child, assigned, depth - 1)

	def _make_header_id(self, header, assigned=None):
		if assigned is None:
			assigned = []
		id = base = re.sub(r'[^\w_-]+', '-', header.title).strip('-')
		i = 1
		while id in assigned:
			i += 1
			id = '%s-%d' % (base, i)
		return id


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
