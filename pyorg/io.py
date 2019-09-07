"""Read (and write) org mode data from JSON and other formats."""

from .ast import OrgDocument, OrgNode, OrgDataNode, NODE_CLASSES, OrgTimestamp
from .util import TreeNamespace, parse_iso_date


JSON_OBJ_DATA_TYPE_KEY = '$$data_type'


def _node_from_json(data, ctx, recurse_contents=True):
	type_ = data['type']
	ref = data['ref']

	# Parse child nodes first
	props = _mapping_from_json(data['properties'], ctx)
	if recurse_contents:
		contents = _list_from_json(data['contents'], ctx)
	else:
		contents = []

	keywords = _mapping_from_json(data.get('keywords', {}), ctx)

	cls = NODE_CLASSES.get(type_, OrgNode)
	node = cls(type_, properties=props, contents=contents, keywords=keywords, ref=ref)

	return node


def _from_json(data, ctx):
	if isinstance(data, list):
		return _list_from_json(data, ctx)

	if isinstance(data, dict):
		data = dict(data)
		datatype = data.pop(JSON_OBJ_DATA_TYPE_KEY, 'mapping')

		if datatype == 'org-node':
			return _node_from_json(data, ctx)

		if datatype == 'mapping':
			return _mapping_from_json(data, ctx)

		if datatype == 'error':
			ctx.errors.append((ctx._path, data['message']))
			print('Parse error:', data['message'])
			return None

		if datatype == 'timestamp':
			return _timestamp_from_json(data, ctx)

		ctx.errors.append((ctx._path, 'Unknown data type in JSON export : %r' % datatype))
		return None

	if isinstance(data, (type(None), bool, int, float, str)):
		return data

	raise TypeError(type(data))


def _list_from_json(data, ctx):
	return [
		_from_json(c, ctx._push(i))
		for (i, c) in enumerate(data)
	]


def _mapping_from_json(data, ctx):
	return {
		k: _from_json(v, ctx._push(k))
		for k, v in data.items() if k != JSON_OBJ_DATA_TYPE_KEY
	}


def _timestamp_from_json(data, ctx):
	return OrgTimestamp(
		data['type'],
		start=None if data.get('start') is None else parse_iso_date(data['start']),
		end=None if data.get('end') is None else parse_iso_date(data['end']),
	)


def _init_ctx(data):
	return TreeNamespace(data=data, errors=[])


def org_doc_from_json(data):
	"""Parse an ORG document from exported JSON data.

	Returns
	-------
	OrgDocument
	"""
	data = dict(data)
	data_type = data.pop(JSON_OBJ_DATA_TYPE_KEY, None)
	if data_type is not None and data_type != 'org-document':
		raise ValueError('Expected data type "org-document", got %r' % data_type)

	ctx = _init_ctx(data)
	contents = _list_from_json(data['contents'], ctx)
	root = OrgDataNode('org-data', contents=contents)

	doc = OrgDocument(root, properties=data['properties'])
	if ctx.errors:
		doc.meta['export_errors'] = ctx.errors

	return doc


def org_node_from_json(data):
	"""Parse an org AST node from JSON data.

	Returns
	-------
	.OrgNode
	"""
	ctx = _init_ctx(data)
	node = _node_from_json(data, ctx)
	if ctx.errors:
		node.meta['export_errors'] = ctx.errors
	return node
