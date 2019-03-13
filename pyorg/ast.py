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
	"""A node in an org file abstract syntaxt tree.
	"""

	def __init__(self, type, props=None, contents=None):
		self.type = type
		self.props = dict(props or {})
		self.contents = list(contents or [])

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


def _from_json(data):
	if isinstance(data, list):
		return list(map(_from_json, data))

	if isinstance(data, dict):
		if 'org_node_type' in data:
			return org_node_from_json(data)
		if '_error' in data:
			print('Parse error:', data['_error'])
			return None
		raise ValueError(data)

	if isinstance(data, (type(None), bool, int, float, str)):
		return data

	raise TypeError(type(data))


def org_node_from_json(data):
	"""Parse an org AST node from JSON data.

	Returns
	-------
	.OrgNode
	"""
	type_ = data['org_node_type']
	props = {k: _from_json(v) for k, v in data['properties'].items()}
	contents = list(map(_from_json, data['contents']))

	return OrgNode(type_, props, contents)
