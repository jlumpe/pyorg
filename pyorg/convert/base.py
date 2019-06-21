from collections import ChainMap
from pyorg.ast import ORG_NODE_TYPES, get_node_type, as_node_type, dispatch_node_type, DispatchNodeType



class OrgConverterMeta(type):

	def __new__(mcls, name, bases, attrs):

		# Merge dictionaries
		for attr in ['DEFAULT_CONFIG']:
			dct = dict()
			for base in bases[::-1]:
				if isinstance(base, OrgConverterMeta):
					dct.update(getattr(base, attr))

			if attr in attrs:
				dct.update(attrs[attr])

			attrs[attr] = dct

		return type.__new__(mcls, name, bases, attrs)



# class OrgConverterBase(metaclass=OrgConverterMeta):
class OrgConverterBase:
	"""Abstract base class for objects which convert org mode AST to another format.

	Attributes
	----------
	config : dict
	"""

	DEFAULT_CONFIG = {
		'image_extensions': ('.png', '.jpg', '.gif', '.tiff'),
		'date_format': '%Y-%m-%d %a',
	}

	def __init__(self, config=None, **kw):
		"""
		Parameters
		----------
		config : dict
			Configuration dictionary to use.
		kw
			Keyword arguments to update configuration with.
		"""
		config = {} if config is None else dict(config)
		if kw:
			config = {**config, **kw}
		self.config = ChainMap(config, self.DEFAULT_CONFIG)

	def convert(self, node):
		ctx = self._init_ctx(node)
		return self._convert(node, ctx)

	def _init_ctx(self, node):
		"""Initialize context dictionary."""
		return {}

	def _convert(self, node, ctx):
		"""Recursively convert an org AST node."""
		raise NotImplementedError()
