"""A DSL for writing Elisp in Python.

God help us all.
"""

from .ast import *


class ElispSingleton:
	"""Singleton object which implements the DSL."""

	__instance = None

	def __new__(cls):
		if cls.__instance is None:
			cls.__instance = object.__new__(cls)
		return cls.__instance

	def __getitem__(self, name):
		"""Indexing with string gets a Symbol."""
		return Symbol(name)

	def _convert_symbol_name(self, name):
		"""Convert symbol name from Python style to Elisp style."""
		return name.replace('_', '-')

	def __getattr__(self, name):
		"""Attribute access with lower-case name gets a symbol."""
		if name[0] == name[0].lower() and not name.startswith('__'):
			return Symbol(self._convert_symbol_name(name))

		return object.__getattribute__(self, name)

	def __call__(self, value):
		"""Calling as function converts value."""
		return to_elisp(value)

	Q = staticmethod(quote)
	C = staticmethod(cons)
	S = staticmethod(symbols)
	R = staticmethod(Raw)


E = ElispSingleton()
