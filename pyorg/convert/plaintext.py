from pyorg.ast import dispatch_node_type, ORG_NODE_TYPES, OrgNode
from .base import OrgConverterBase


class OrgPlaintextConverter(OrgConverterBase):

	def convert_multi(self, items, blanks=False, sep=None):
		ctx = self._init_ctx(None, {})
		return self._convert_contents(items, ctx, blanks=blanks, sep=sep)

	def _convert_contents(self, contents, ctx, blanks=False, sep=None):
		"""Convert contents of a node to plaintext.

		Parameters
		----------
		contents : list
			List of org nodes or strings.
		blanks : bool
			Prepend and append whitespace according to the ``pre-blank`` and
			``post-blank`` properties.
		sep : str
			Separator to use.

		Returns
		-------
		str
		"""
		contents_str = []

		for i, item in enumerate(contents):
			if isinstance(item, OrgNode):
				txt = self._convert(item, ctx._push(i))
				if blanks:
					pre = ' ' * item.properties.get('pre-blank', 0)
					post = ' ' * item.properties.get('post-blank', 0)
					txt = pre + txt + post
				contents_str.append(txt)

			elif isinstance(item, str):
				contents_str.append(item)

			else:
				raise TypeError(item)

		if sep is None:
			sep = '' if blanks else ' '
		return sep.join(contents_str)

	@dispatch_node_type()
	def _convert(self, node, ctx):
		return "<Can't convert %s node to plain text>" % node.type.name

	@_convert.register(['section'])
	def _convert_element_contents(self, node, ctx):
		return self._convert_contents(node.contents, ctx, sep='\n\n')

	@_convert.register([nt.name for nt in ORG_NODE_TYPES.values() if nt.is_object_container])
	def _convert_object_container(self, node, ctx):
		return self._convert_contents(node.contents, ctx, blanks=True)

	@_convert.register([
		'code', 'comment', 'comment-block', 'latex-fragment',
		'verbatim', 'example-block', 'statistics-cookie', 'fixed-width', 'src-block'
	])
	def _convert_from_value(self, node, ctx):
		return node['value']

	@_convert.register('line-break')
	def _convert_line_break(self, node, ctx):
		return '\n'

	@_convert.register('timestamp')
	def _convert_timestamp(self, node, ctx):
		return node['raw-value']

	@_convert.register('link')
	def _convert_link(self, node, ctx):
		if node.contents:
			return self._convert_object_container(node, ctx)
		else:
			return node['raw-link']

	@_convert.register('entity')
	def _convert_entity(self, node, ctx):
		return node['utf-8']


def to_plaintext(arg, blanks=False, sep=None, **kwargs):
	converter = OrgPlaintextConverter(**kwargs)
	if isinstance(arg, OrgNode):
		return converter.convert(arg)
	else:
		return converter.convert_multi(arg, blanks=blanks, sep=sep)
