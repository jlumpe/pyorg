"""Read (and write) org mode data from JSON and other formats."""

from .ast import OrgNode, NODE_CLASSES
from pyorg.parse import parse_tags
from .agenda import OrgAgendaItem


JSON_OBJ_DATA_TYPE_KEY = '$$data_type'


def _node_from_json(data, **kw):
	type_ = data['org_node_type']

	# Parse child nodes first
	props = _mapping_from_json(data['properties'], **kw)
	if kw.get('recurse_contents', True):
		contents = [_from_json(c, **kw) for c in data['contents']]
	else:
		contents = []
	keywords = _mapping_from_json(data.get('keywords', {}), **kw)

	cls = NODE_CLASSES.get(type_, OrgNode)
	node = cls(type_, props=props, contents=contents, keywords=keywords)

	return node


def _from_json(data, **kw):
	if isinstance(data, list):
		return [_from_json(item, **kw) for item in  data]

	if isinstance(data, dict):
		data = dict(data)
		datatype = data.pop(JSON_OBJ_DATA_TYPE_KEY, 'mapping')
		if datatype == 'org':
			return _node_from_json(data, **kw)
		if datatype == 'mapping':
			return _mapping_from_json(data, **kw)
		if datatype == 'error':
			print('Parse error:', data['message'])
			return None
		raise ValueError(data)

	if isinstance(data, (type(None), bool, int, float, str)):
		return data

	raise TypeError(type(data))


def _mapping_from_json(data, **kw):
	return {k: _from_json(v, **kw) for k, v in data.items() if k != JSON_OBJ_DATA_TYPE_KEY}


def org_node_from_json(data):
	"""Parse an org AST node from JSON data.

	Returns
	-------
	.OrgNode
	"""
	return _node_from_json(data)


def agenda_item_from_json(data):
	"""Parse an agenda item from JSON data.

	Parameters
	----------
	data : dict

	Returns
	-------
	.OrgAgendaItem
	"""
	node_json = data.pop('node')
	headline = _node_from_json(node_json, recurse_contents=False)
	item = _mapping_from_json(data)

	attrs = {'headline': headline}
	attrmap = {
		'type': 'type',
		'keyword': 'todo',
		'headline_path': 'path',
		'file': 'file-relative',
		'deadline': 'deadline',
		'view_priority': 'priority',
		'priority': 'priority-letter',
		'category': 'category',
	}
	for attr, key in attrmap.items():
		try:
			attrs[attr] = item.pop(key)
		except KeyError:
			pass

	# Get rich and plain text from headline node if possible
	txt = item.pop('txt')
	if headline is not None:
		text = headline['title']
		attrs['text_plain'] = headline.title
	else:
		text = [txt]
		attrs['text_plain'] = txt

	# attrs['tags'] = parse_tags(item.pop('tags', None) or '')
	attrs['tags'] = item.pop('tags')

	ignore = {
		'file', 'done-face', 'help-echo', 'mouse-face', 'org-not-done-regexp',
		'org-complex-heading-regexp', 'org-todo-regexp',
	}
	for key in ignore:
		item.pop(key)

	return OrgAgendaItem(text, **attrs, **item)
