"""Read (and write) org mode data from JSON and other formats."""

from .ast import OrgNode, NODE_CLASSES


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
