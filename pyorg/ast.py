"""Work with org file abstract syntax trees."""


class OrgElement:
	"""An elemment (or object) in an org file.

	Corresponds to a node in the org file AST.
	"""

	def __init__(self, type, props=None, contents=None):
		self.type = type
		self.props = dict(props or {})
		self.contents = list(contents or [])

	@property
	def children(self):
		return [c for c in self.contents if isinstance(c, OrgElement)]

	def __repr__(self):
		return '%s(type=%r)' % (type(self).__name__, self.type)

	def dump(self, index=None, indent=''):
		"""Print a debug representation of the element and its descendants."""
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
			if isinstance(child, OrgElement):
				child.dump(i, indent + '  ')
			else:
				print('%s%d %r' % (indent, i, child))

		print_()


def _from_json(data):
	if isinstance(data, list):
		return list(map(_from_json, data))

	if isinstance(data, dict):
		if 'org_element_type' in data:
			return org_elem_from_json(data)
		if '_error' in data:
			print('Parse error:', data['_error'])
			return None
		raise ValueError(data)

	if isinstance(data, (type(None), bool, int, float, str)):
		return data

	raise TypeError(type(data))


def org_elem_from_json(data):
	"""Parse an org mode element from JSON data.

	Returns
	-------
	.OrgElement
	"""
	type_ = data['org_element_type']
	props = {k: _from_json(v) for k, v in data['properties'].items()}
	contents = list(map(_from_json, data['contents']))

	return OrgElement(type_, props, contents)
