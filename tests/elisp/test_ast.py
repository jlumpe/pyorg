"""Test Elisp AST node classes."""

import pyorg.elisp as el


# Some reusable node constants
T = el.Symbol('t')
NIL = el.Symbol('nil')

SYMBOLS = [T, NIL] + list(map(el.Symbol, ['foo', ':foo', 'bar']))
LITERALS = list(map(el.Literal, [0, 1, -1, 0.0, 1.0, "foo", "bar", ""]))
CONS = [el.Cons(el.Literal(0), el.Literal(1)), el.Cons(el.Symbol('foo'), el.Literal('bar'))]
LISTS = list(map(el.List, [
	[],
	[el.Literal(i) for i in range(1, 4)],
	[el.Literal(s) for s in ['foo', 'bar', 'baz']],
]))
QUOTES = [el.Quote(n) for l in [SYMBOLS, LITERALS, CONS, LISTS] for n in l[:2]]

NODES = SYMBOLS + LITERALS + CONS + LISTS


def test_equality():
	"""Test equality of AST nodes."""

	for l in LITERALS:
		assert l == el.Literal(l.pyvalue)

	for s in SYMBOLS:
		assert s == el.Symbol(s.name)

	for c in CONS:
		assert c == el.Cons(c.car, c.cdr)

	for l in LISTS:
		assert l == el.List(l.items)

	for q in QUOTES:
		assert q == el.Quote(q.form)

	# Check inequality - these should all be pairwise unequal
	for i, item1 in enumerate(NODES):
		for item2 in NODES[i + 1:]:
			assert item1 != item2

			# Check quoted versions of pair as well
			assert el.Quote(item1) != el.Quote(item2)
			assert el.Quote(item1) != item1
			assert el.Quote(item1) != item2
			assert el.Quote(item2) != item1
			assert el.Quote(item2) != item2


def test_convert():
	"""Test conversion of Python values."""

	# Bools and none to t and nil
	assert el.to_elisp(None) == el.Symbol('nil')
	assert el.to_elisp(False) == el.Symbol('nil')
	assert el.to_elisp(True) == el.Symbol('t')

	# Wrap numbers and strings in literals
	assert el.to_elisp(1) == el.Literal(1)
	assert el.to_elisp(1.0) == el.Literal(1.0)
	assert el.to_elisp("foo") == el.Literal("foo")

	# Tuples to lists
	tup = ((3.14, "bar", NIL, (1, 2)))
	assert el.to_elisp(tup) == el.make_list(tup)

	# Should leave existing nodes unchanged
	for n in NODES:
		assert el.to_elisp(n) == n


def test_make_list():
	assert el.to_elisp((3.14, "bar", NIL, (1, 2))) == \
	       el.List([el.Literal(3.14), el.Literal("bar"), NIL,
	                el.List([el.Literal(1), el.Literal(2)])])
