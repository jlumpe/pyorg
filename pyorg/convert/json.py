"""Convert org mode AST nodes to JSON."""

from collections.abc import Sequence, Mapping

from .base import OrgConverterBase
from ..ast import dispatch_node_type, OrgNode


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
	def _convert_node(self, node, ctx):
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
			key: self._convert(value, ctx)
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
		return self._convert_node(child, ctx)

	def _convert(self, value, ctx):
		if isinstance(value, OrgNode):
			return self._convert_node(value, ctx)
		if isinstance(value, (str, int, float, bool, type(None))):
			return value
		if isinstance(value, Sequence):
			return [self._convert(item, ctx) for item in value]
		if isinstance(value, Mapping):
			return self._convert_mapping(value, ctx)

		raise TypeError("Can't convert object of type %r" % type(value))

	def _convert_mapping(self, value, ctx):
		converted = {}
		for k, v in value.items():
			assert isinstance(k, str)
			converted[k] = self._convert(v, ctx)

		return self.make_object('mapping', converted)


def to_json(node, **kwargs):
	converter = OrgJsonConverter(**kwargs)
	return converter.convert(node)
