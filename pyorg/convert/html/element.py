from html import escape
from io import StringIO


class TextNode:
	"""Text node to be used within HTML.

	Attributes
	----------
	text : str
		Wrapped text.
	post_ws : bool
		Whether to add whitespace after the tag when rendering in an inline
		context.
	"""

	def __init__(self, text, post_ws=False):
		self.text = text
		self.post_ws = post_ws

	def __str__(self):
		return escape(self.text)


class HtmlElement:
	"""Lightweight class to represent an HTML element.

	Attributes
	----------
	tag : str
		HTML tag name (minus angle brackets).
	children : list
		List of child elements (``HtmlElement`` or strings).
	attrs : dict
		Mapping from attributes names (strings) to values (strings or bools).
	inline : bool
		Whether to render children in an inline context. If False each child
		will be rendered on its own line. If True whitespace will only be added
		before/after children according to the :attr:`post_ws` attribute of the
		child.
	classes : list
		List of class names present in the "class" attribute. Assignable property.
	post_ws : bool
		Whether to add whitespace after the tag when rendering in an inline
		context.
	"""

	def __init__(self, tag, children=None, attrs=None, inline=False, post_ws=False):
		self.tag = tag
		self.children = list(children or [])
		self.attrs = dict(attrs or [])
		self.inline = inline
		self.post_ws = post_ws

	@property
	def classes(self):
		s = self.attrs.get('class', '').strip()
		return s.split() if s else []

	@classes.setter
	def classes(self, value):
		if not isinstance(value, str):
			value = ' '.join(value)
		self.attrs['class'] = value

	def add_class(self, classes):
		current = self.classes

		if isinstance(classes, str):
			classes = classes.split()

		for cls in classes:
			if cls not in current:
				current.append(cls)

		self.classes = current

	def __repr__(self):
		return '<' + self.tag + (' ...' if self.attrs else '') + ('>...</' + self.tag if self.children else '/>')

	def __str__(self):
		return html_to_string(self)


def _write_html_recursive(stream, elem, indent, depth, inline=False):
	inline = inline or elem.inline

	# Opening tag and attrs
	stream.write('<' + elem.tag)

	for key, value in elem.attrs.items():
		if isinstance(value, str):
			stream.write(' %s="%s"' % (escape(key), escape(value)))
		elif isinstance(value, bool):
			if value:
				stream.write(' %s' % escape(key))
		else:
			raise TypeError(type(value))

	stream.write('>')

	for child in elem.children:
		if not inline:
			stream.write('\n')
			stream.write(indent * (depth + 1))

		post_ws = False

		if isinstance(child, str):
			stream.write(escape(child))
		elif isinstance(child, TextNode):
			stream.write(escape(child.text))
			post_ws = child.post_ws
		elif isinstance(child, HtmlElement):
			_write_html_recursive(stream, child, indent=indent, depth=depth + 1, inline=inline)
			post_ws = child.post_ws
		else:
			raise TypeError(type(child))

		if inline and post_ws:
			stream.write(' ')

	if elem.children and not inline:
		stream.write('\n')
		stream.write(indent * depth)

	stream.write('</%s>' % elem.tag)


def write_html(stream, elem, indent='\t', inline=False):
	_write_html_recursive(stream, elem, indent, depth=0, inline=inline)


def html_to_string(elem, **kwargs):
	buf = StringIO()
	write_html(buf, elem, **kwargs)
	return buf.getvalue()
