"""Convert org mode AST nodes to JSON."""

from .base import OrgConverterBase
from ..ast import dispatch_node_type, OrgNode
from ..util import SingleDispatch


class OrgJsonConverter(OrgConverterBase):
	DEFAULT_CONFIG = {
		'object_type_key': '$$data_type',
		**OrgConverterBase.DEFAULT_CONFIG
	}

	def make_object(self, type_, data):
		key = self.config.get('object_type_key')
		if key is not None:
			assert key not in data
			return {key: type_, **data}

		return data

	@dispatch_node_type()
	def _convert(self, node, ctx):
		properties = self._convert_properties(node, ctx)
		children = self._convert_children(node, ctx)
		return self.make_object('node', {
			'type': node.type.name,
			'properties': self.make_object('mapping', properties),
			'children': children,
		})

	@dispatch_node_type()
	def _convert_properties(self, node, ctx):
		return {
			key: self._convert_generic(value, ctx)
			for key, value in node.props.items()
		}

	@dispatch_node_type()
	def _convert_children(self, node, ctx):
		converted = []
		for child in node.children:
			c = self._convert_child(node, child, ctx)
			if c is not None:
				converted.append(c)

		return converted

	@dispatch_node_type()
	def _convert_child(self, node, child, ctx):
		return self._convert(child, ctx)

	@SingleDispatch
	def _convert_generic(self, value, ctx):
		raise TypeError("Can't convert object of type %r" % type(value))

	_convert_generic.register([str, int, float, bool, type(None)], lambda s, v, c: v)
	_convert_generic.register(OrgNode, _convert)
	_convert_generic.register(list, lambda s, v, c: [s._convert_generic(item, c) for item in v])

	@_convert_generic.register(dict)
	def _convert_dict(self, value, ctx):
		converted = {}
		for k, v in value.items():
			assert isinstance(k, str)
			converted[k] = self._convert_generic(v, ctx)

		return self.make_object('mapping', converted)


def to_json(node, **kwargs):
	converter = OrgJsonConverter(**kwargs)
	return converter.convert(node)
