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
		contents = self._convert_contents(node, ctx)
		return self.make_object('node', {
			'type': node.type.name,
			'properties': self.make_object('mapping', properties),
			'contents': contents,
		})

	@_convert_node.register(['org-data', 'headline'])
	def _convert_outline_node(self, node, ctx):
		obj = self._convert_node.default(node, ctx)
		obj['title_plain'] = self._convert(node.title, ctx)
		obj['title'] = self._convert(node.title, ctx)
		return obj

	@dispatch_node_type()
	def _convert_properties(self, node, ctx):
		return {
			key: self._convert(value, ctx._push(key))
			for key, value in node.properties.items()
		}

	@dispatch_node_type()
	def _convert_contents(self, node, ctx):
		converted = []
		for i, item in enumerate(node.contents):
			c = self._convert_contents_item(node, item, ctx._push(i))
			if c is not None:
				converted.append(c)

		return converted

	@dispatch_node_type()
	def _convert_contents_item(self, node, item, ctx):
		return self._convert(item, ctx)

	def _convert(self, value, ctx):
		if isinstance(value, OrgNode):
			return self._convert_node(value, ctx)
		if isinstance(value, (str, int, float, bool, type(None))):
			return value
		if isinstance(value, Sequence):
			return [self._convert(item, ctx._push(i)) for i, item in enumerate(value)]
		if isinstance(value, Mapping):
			return self._convert_mapping(value, ctx)

		raise TypeError("Can't convert object of type %r" % type(value))

	def _convert_mapping(self, value, ctx):
		converted = {}
		for k, v in value.items():
			assert isinstance(k, str)
			converted[k] = self._convert(v, ctx._push(k))

		return self.make_object('mapping', converted)


def to_json(node, **kwargs):
	converter = OrgJsonConverter(**kwargs)
	return converter.convert(node)
