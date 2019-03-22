"""
Work with org file abstract syntax trees.

See https://orgmode.org/worg/dev/org-syntax.html for a description of the org
syntax.
"""


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

	def __init__(self, type, props=None, contents=None, keywords=None, parent=None, outline=None):
		self.type = type
		self.props = dict(props or {})
		self.keywords = dict(keywords or {})
		self.contents = list(contents or [])
		self.parent = parent
		self.outline = outline

	@property
	def children(self):
		return [c for c in self.contents if isinstance(c, OrgNode)]

	def __repr__(self):
		return '%s(type=%r)' % (type(self).__name__, self.type)

	def __len__(self):
		return len(self.children)

	def __iter__(self):
		return iter(self.children)

	def __getitem__(self, key):
		if isinstance(key, int):
			return self.children[key]
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
	children : list
		Child outline nodes.
	"""

	is_outline = True

	def __init__(self, type, level=None, title=None, id=None, section=None, children=None, **kw):
		super().__init__(type, **kw)
		self.level = level
		self.title = title
		self.id = None
		self.section = section
		self.outline_children = children


def _node_from_json(data, parent=None, outline=None, title=None, **kw):
	type_ = data['org_node_type']
	is_outline = type_ in ('org-data', 'headline')

	# Create empty node
	if is_outline:
		node = OrgOutlineNode(type_, parent=parent, outline=outline)
		child_outline = node
	else:
		node = OrgNode(type_, parent=parent, outline=outline)
		child_outline = outline

	child_kw = {'parent': node, 'outline': child_outline, **kw}

	# Create children with correct parent and add to parent
	for key, value in data['properties'].items():
		node.props[key] = _from_json(value, **child_kw)
	for key, value in data['keywords'].items():
		node.keywords[key] = _from_json(value, **child_kw)
	for item in data['contents']:
		node.contents.append(_from_json(item, **child_kw))

	if is_outline:
		node.level = node['level'] if type_ == 'headline' else 0

		children = list(node.contents)

		# Section should be first node in contents, if it exists
		if children and children[0].type == 'section':
			node.section = children.pop(0)

		# Remainder should be outline nodes (specifically headlines)
		assert all(child.is_outline for child in children)
		node.outline_children = children

		# Get default title
		if title is None:
			if type_ == 'headline':
				title = node['raw-value']
			else:
				title = node.section.keywords.get('TITLE')

		node.title = title

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


def assign_outline_ids(root):
	"""Assign unique IDs to outline nodes."""
	assigned = {}
	for child in root.outline_children:
		_assign_outline_ids(child, assigned)
	return assigned

import re

def _assign_outline_ids(node, assigned):
	id = base = re.sub(r'[^\w_-]+', '-', node.title).strip('-')
	i = 1
	while id in assigned:
		i += 1
		id = '%s-%d' % (base, i)
	node.id = id
	assigned[id] = node

	for child in node.outline_children:
		_assign_outline_ids(child, assigned)

