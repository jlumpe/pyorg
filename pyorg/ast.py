"""
Work with org file abstract syntax trees.

See https://orgmode.org/worg/dev/org-syntax.html for a description of the org
syntax.
"""

import re
from collections.abc import Iterable
from datetime import datetime


# org-element-all-elements
# "An element defines syntactical parts that are at the same level as a paragraph,
# i.e. which cannot contain or be included in a paragraph."
ORG_ALL_ELEMENTS = frozenset({
	'babel-call', 'center-block', 'clock', 'comment', 'comment-block',
	'diary-sexp', 'drawer', 'dynamic-block', 'example-block', 'export-block',
	'fixed-width', 'footnote-definition', 'headline', 'horizontal-rule',
	'inlinetask', 'item', 'keyword', 'latex-environment', 'node-property',
	'paragraph', 'plain-list', 'planning', 'property-drawer', 'quote-block',
	'section', 'special-block', 'src-block', 'table', 'table-row', 'verse-block',
})

# org-element-greater-elements
# "Greater elements are all parts that can contain an element."
ORG_GREATER_ELEMENTS = frozenset({
	'center-block', 'drawer', 'dynamic-block', 'footnote-definition', 'headline',
	'inlinetask', 'item', 'plain-list', 'property-drawer', 'quote-block',
	'section', 'special-block', 'table',
})

# org-element-all-objects
# "An object is a part that could be included in an element."
ORG_ALL_OBJECTS = frozenset({
	'bold', 'code', 'entity', 'export-snippet', 'footnote-reference',
	'inline-babel-call', 'inline-src-block', 'italic', 'line-break',
	'latex-fragment', 'link', 'macro', 'radio-target', 'statistics-cookie',
	'strike-through', 'subscript', 'superscript', 'table-cell', 'target',
	'timestamp', 'underline', 'verbatim',
})

# org-element-object-containers
ORG_OBJECT_CONTAINERS = frozenset({
	'bold', 'footnote-reference', 'italic', 'link', 'subscript', 'radio-target',
	'strike-through', 'superscript', 'table-cell', 'underline', 'paragraph',
	'table-row', 'verse-block',
})

# org-element-recursive-objects
ORG_RECURSIVE_OBJECTS = frozenset({
	'bold', 'footnote-reference', 'italic', 'link', 'subscript', 'radio-target',
	'strike-through', 'superscript', 'table-cell', 'underline',
})

ORG_ALL_NODE_TYPES = set.union(*map(set, [ORG_ALL_ELEMENTS, ORG_ALL_OBJECTS]))


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

	type: str
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
		return '%s(type=%r)' % (type(self).__name__, self.type)

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

	def dump(self, index=None, indent=''):
		"""Print a debug representation of the node and its descendants."""
		def print_(*args):
			print(indent, end='')
			print(*args)

		if index is None:
			print_(self.type)

		else:
			print_(index, self.type)

		for key in sorted(self.props):
			value = self.props[key]
			print_('  :%-10s : %r' % (key, value))

		print_()

		for i, child in enumerate(self.contents):
			if isinstance(child, OrgNode):
				child.dump(i, indent + '  ')
			else:
				print('%s%d %r' % (indent, i, child))

		print_()


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
		if self.contents and self.contents[0].type == 'section':
			self.section = self.contents[0]
		else:
			self.section = None


		# Default title
		if title is None:
			if type_ == 'headline':
				title = self['raw-value']
			else:
				title = self.section.keywords.get('TITLE')

		self.title = title
		self.id = id

		self.level = self['level'] if type_ == 'headline' else 0

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
		assert type_ == 'timestamp'
		super().__init__(type_, *args, **kwargs)

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


def _node_from_json(data, **kw):
	type_ = data['org_node_type']

	# Parse child nodes first
	props = _mapping_from_json(data['properties'], **kw)
	contents = [_from_json(c, **kw) for c in data['contents']]
	keywords = _mapping_from_json(data.get('keywords', {}), **kw)

	cls = NODE_CLASSES.get(type_, OrgNode)
	node = cls(type_, props=props, contents=contents, keywords=keywords)

	return node


def _from_json(data, **kw):
	if isinstance(data, list):
		return [_from_json(item, **kw) for item in  data]

	if isinstance(data, dict):
		if 'org_node_type' in data:
			return _node_from_json(data, **kw)
		if '_error' in data:
			print('Parse error:', data['_error'])
			return None
		raise ValueError(data)

	if isinstance(data, (type(None), bool, int, float, str)):
		return data

	raise TypeError(type(data))


def _mapping_from_json(data, **kw):
	return {k: _from_json(v, **kw) for k, v in data.items()}


def org_node_from_json(data):
	"""Parse an org AST node from JSON data.

	Returns
	-------
	.OrgNode
	"""
	return _node_from_json(data)


def get_node_type(obj):
	"""Get type of AST node, returning None for other types."""
	return obj.type if isinstance(obj, OrgNode) else None


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
