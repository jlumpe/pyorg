from collections import ChainMap
from pyorg.util import TreeNamespace


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

	def convert(self, node, **kwargs):
		ctx = self._init_ctx(node, kwargs)
		return self._convert(node, ctx)

	def _init_ctx(self, root, kwargs):
		"""Initialize context namespace."""
		return TreeNamespace(root=root, kwargs=kwargs)

	def _convert(self, node, ctx):
		"""Recursively convert an org AST node."""
		raise NotImplementedError()
