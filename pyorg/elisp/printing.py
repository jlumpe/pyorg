"""Print Elisp AST to code."""

from functools import singledispatch
import re

from .ast import *


def print_elisp_string(string):
	"""Print string to Elisp, properly escaping it (maybe)."""
	return '"%s"' % re.sub(r'([\\\"])', r'\\\1', string)


@singledispatch
def print_elisp(node):
	"""Print an Elisp AST node."""
	raise TypeError("Don't know how to print objects of type %s" % type(node).__name__)


@print_elisp.register(Literal)
def _print_literal(literal):
	if isinstance(literal.pyvalue, str):
		return print_elisp_string(literal.pyvalue)
	else:
		return str(literal.pyvalue)


@print_elisp.register(Symbol)
def _print_symbol(symbol):
	return symbol.name


@print_elisp.register(Cons)
def _print_cons(cons):
	return '(%s . %s)' % (print_elisp(cons.car), print_elisp(cons.cdr))


@print_elisp.register(List)
def _print_list(list_):
	return '(%s)' % ' '.join(map(print_elisp, list_.items))


@print_elisp.register(Quote)
def _print_quote(quote):
	return "'" + print_elisp(quote.form)


@print_elisp.register(Raw)
def _print_raw(raw):
	return raw.src
