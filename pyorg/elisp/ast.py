"""Base classes for Emacs Lisp abstract syntax trees."""

from functools import singledispatch


__all__ = ['ElispAstNode', 'Form', 'Literal', 'Symbol', 'Cons', 'List', 'Quote',
           'Raw', 'to_elisp', 'make_list', 'symbols', 'quote', 'cons']


class ElispAstNode:
	"""Abstract base class for Elisp AST nodes."""

	def __repr__(self):
		return '<el %s>' % self

	def __str__(self):
		from .printing import print_elisp
		return print_elisp(self)


class Form(ElispAstNode):
	"""Pretty much everything is a form, right?"""


class Literal(Form):
	"""Basic self-evaluating forms like strings, numbers, etc."""

	PY_TYPES = (str, int, float)

	def __init__(self, pyvalue):
		assert isinstance(pyvalue, self.PY_TYPES)
		self.pyvalue = pyvalue

	def __eq__(self, other):
		return isinstance(other, Literal) \
		       and type(other.pyvalue) is type(self.pyvalue) \
		       and other.pyvalue == self.pyvalue


class Symbol(Form):
	"""Elisp symbol."""

	def __init__(self, name):
		assert isinstance(name, str) and name
		self.name = name

	def __eq__(self, other):
		return isinstance(other, Symbol) and other.name == self.name

	@property
	def isconst(self):
		return self.name.startswith(':') or self.name in ('nil', 't')

	def __call__(self, *args):
		"""Produce a function call node from this symbol."""
		return List((self, *map(to_elisp, args)))


class Cons(Form):
	"""A cons cell."""

	def __init__(self, car, cdr):
		assert isinstance(car, Form)
		assert isinstance(cdr, Form)
		self.car = car
		self.cdr = cdr

	def __eq__(self, other):
		return isinstance(other, Cons) \
		       and other.car == self.car \
		       and other.cdr == self.cdr


class List(Form):
	"""A list..."""

	islist = False

	def __init__(self, items):
		self.items = tuple(items)

	def __eq__(self, other):
		return isinstance(other, List) and other.items == self.items


class Quote(Form):
	"""A quoted Elisp form."""

	def __init__(self, form):
		assert isinstance(form, Form)
		self.form = form

	def __eq__(self, other):
		return isinstance(other, Quote) and other.form == self.form


class Raw(ElispAstNode):
	"""Just raw code to be pasted in at this point."""

	def __init__(self, src):
		self.src = src

	def __eq__(self, other):
		return isinstance(other, Raw) and other.src == self.src


@singledispatch
def to_elisp(value):
	"""Convert a Python value to an Elisp AST node."""
	if isinstance(value, ElispAstNode):
		return value
	raise TypeError('Cannot convert object of type %s to Elisp' % type(value).__name__)


@to_elisp.register(bool)
@to_elisp.register(type(None))
def _bool_to_elisp(value):
	return Symbol('t') if value else Symbol('nil')


# Register literal types
for type_ in Literal.PY_TYPES:
	to_elisp.register(type_, Literal)


# Convert Python lists to quoted Emacs lists
@to_elisp.register(list)
def _py_list_to_el_list(pylist):
	return Quote(make_list(pylist))


@to_elisp.register(tuple)
def make_list(items):
	"""Make an Elisp list from a Python sequence, first converting its elements to Elisp."""
	return List(map(to_elisp, items))


def quote(value):
	"""Quote value, converting Python strings to symbols."""
	if isinstance(value, str):
		form = Symbol(value)
	else:
		form = to_elisp(value)

	return Quote(form)


def cons(car, cds):
	"""Create a Cons cell, converting arguments."""
	return Cons(to_elisp(car), to_elisp(cds))


def symbols(*names):
	"""Create a list of symbols."""

	s = []

	for name in names:
		if isinstance(name, str):
			s.append(Symbol(name))
		elif isinstance(name, Symbol):
			s.append(name)
		else:
			raise TypeError('Expected str or Symbol, got %s' % type(name).__name__)

	return List(s)
