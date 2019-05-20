"""Export org mode AST nodes to HTML."""

from collections import ChainMap
from html import escape
from io import StringIO

from .ast import ORG_ALL_OBJECTS, get_node_type


class HtmlElement:
	"""Lightweight class to represent an HTML element.

	Attributes
	----------
	tag : str
	children : list
	attrs : dict
	inline : bool
	classes : list
	"""

	def __init__(self, tag, children=None, attrs=None, inline=False):
		self.tag = tag
		self.children = list(children or [])
		self.attrs = dict(attrs or [])
		self.inline = inline

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
		stream.write(' %s="%s"' % (escape(key), escape(value)))

	stream.write('>')

	for child in elem.children:
		if not inline:
			stream.write('\n')
			stream.write(indent * (depth + 1))

		if isinstance(child, str):
			stream.write(escape(child))
		else:
			_write_html_recursive(stream, child, indent=indent, depth=depth + 1, inline=inline)

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


class DispatchNodeType:

	def __init__(self, default, registry=None, instance=None):
		self.default = default
		self.registry = {} if registry is None else registry
		self.instance = instance

	def bind(self, instance):
		return DispatchNodeType(self.default, self.registry, instance)

	def unbind(self):
		return DispatchNodeType(self.default, self.registry, None)

	def __get__(self, instance, owner):
		if instance is None:
			return self
		return self.bind(instance)

	def dispatch(self, type_):
		method = self.registry.get(type_, self.default)
		if self.instance is not None:
			method.__get__(self.instance, type(self.instance))
		return method

	def register(self, type_):
		def decorator(method):
			self.registry[type_] = method
			return method

		return decorator

	def __call__(self, *args, **kwargs):
		if self.instance is not None:
			return self._call(self.instance, *args, **kwargs)
		return self._call(*args, **kwargs)

	def _call(self, instance, node, *args, **kwargs):
		method = self.dispatch(node.type)
		return method(instance, node, *args, **kwargs)


def dispatch_node_type(parent=None):
	registry = {} if parent is None else ChainMap(parent, {})

	def decorator(default):
		return DispatchNodeType(default, registry)

	return decorator


class OrgHtmlConverter:

	# Default HTML tag for each node type. None means to skip.
	TAGS = {
		'org-data': 'div',
		'item': 'li',
		'paragraph': 'p',
		'bold': 'strong',
		'code': 'code',
		'italic': 'em',
		'link': 'a',
		'strike-through': 's',
		'verbatim': 'span',
		'superscript': 'sup',
		'subscript': 'sub',
		'underline': 'u',
		'section': 'div',
		'comment': None,
		'example-block': 'pre',
		'quote-block': 'blockquote',
		'verse-block': 'p',
		'center-block': 'div',  # Contains paragraph node?
		'timestamp': 'span',
		'statistics-cookie': 'span',
	}

	INLINE_NODES = frozenset({
		'paragraph', 'example-block', 'fixed-width',
		*ORG_ALL_OBJECTS,
	})

	DEFAULT_CONFIG = {
		'latex_delims': ('$$', '$$'),
		'latex_inline_delims': (r'\(', r'\)'),
		'date_format': '%Y-%m-%d %a',
	}

	def __init__(self, config=None, **kw):
		if config is None:
			config = {}
		if kw:
			config = {**config, **kw}
		self.config = ChainMap(self.DEFAULT_CONFIG, config)

	def default_tag(self, type_):
		try:
			return self.TAGS[type_]
		except KeyError:
			return 'span' if type_ in ORG_ALL_OBJECTS else 'div'

	def convert(self, node, dom=False):
		"""Convert org node to HTML.

		Parameters
		---------
		node : pyorg.ast.OrgNode
			Org node to convert.
		dom : bool
			Return HTML element instead of string.

		Returns
		-------
		str or HtmlElement
		"""
		elem = self._convert(node, None)

		if dom:
			return elem

		return str(elem)

	def _convert(self, what, ctx):
		"""Convert an org AST node OR text to HTML element."""
		if isinstance(what, str):
			return what
		else:
			return self._convert_node(what, ctx)

	def _convert_node_default(self, node, ctx, **kwargs):
		html = self._make_elem(node, ctx, **kwargs)
		self._add_children(html, node.contents, ctx)
		return html

	_convert_node = dispatch_node_type()(_convert_node_default)
	_convert_node.__doc__ = """Recursively _convert an org AST node to HTML."""

	def _make_elem_base(self, tag, text=None, attrs=None, classes=None, inline=False):
		"""Create a new HTML element."""
		html = HtmlElement(tag, inline=inline)
		if text is not None:
			html.children.append(text)
		if attrs is not None:
			html.attrs.update(attrs)
		if classes is not None:
			html.classes = classes
		return html

	def _make_elem_default(self, node, ctx, tag=None, **kwargs):
		no_default = False

		if tag is None:
			tag = self.default_tag(node.type)
			if node.type not in self.TAGS:
				no_default = True

			if tag is None:
				return None

		kwargs.setdefault('inline', node.type in self.INLINE_NODES)

		html = self._make_elem_base(tag, **kwargs)
		html.add_class('org-node org-%s' % node.type)

		# Warn about no default tag
		if no_default:
			msg = "Don't know how to convert node of type %r" % node.type
			self._add_error(html)
			html.children.append(self._make_error_msg(msg))

		return html

	_make_elem = dispatch_node_type()(_make_elem_default)
	_make_elem.__doc__ = """
	Make the HTML element for a given org node (but do not recurse to
	children).
	"""

	def _add_children(self, parent, org_nodes, ctx):
		"""Recursively _convert org AST nodes and add to parent html element."""
		for node in org_nodes:
			html = self._convert(node, ctx)
			if html is not None:
				parent.children.append(html)

	def make_headline_text(self, node, ctx=None, dom=False):
		"""Make HTML element for text content of headline node."""
		elem = self._make_elem_base('span', classes='org-header-text')
		self._add_children(elem, node['title'], ctx)

		if dom:
			return elem

		return str(elem)

	@_make_elem.register('headline')
	def _make_headline(self, node, ctx):
		assert node.is_outline

		html = HtmlElement('div')
		html.classes = 'org-header-container org-header-level-%d' % node.level

		h_level = tag = 'h%d' % min(node.level + 1, 6)
		header = self._make_elem_default(node, ctx, tag=tag, inline=True)
		html.children.append(header)

		# ID
		if node.id:
			html.attrs['id'] = node.id

		# TODO info
		todo_type = node.props['todo-type']

		if todo_type:
			todo_kw = node.props['todo-keyword']

			html.add_class('org-has-todo')
			html.add_class('org-todo-%s' % todo_type)
			html.add_class('org-todo-kw-%s' % todo_kw)

			header.children.append(self._make_elem_base(
				'span',
				text=todo_kw,
				classes='org-todo org-todo-%s' % todo_type,
			))
			header.children.append(' ')

			priority_code = node.props['priority']

			if priority_code is not None:
				priority_char = chr(priority_code)
				header.children.append(self._make_elem_base(
					'span',
					text=priority_char,
					classes='org-todo-priority org-todo-priority-%s' % priority_char,
				))
				header.children.append(' ')

		# Text
		header_text = self.make_headline_text(node, ctx, dom=True)
		header.children.append(header_text)

		# Tags
		tags = node.props['tags']
		if tags:
			tags_elem = self._make_elem_base('span', classes='org-tags')

			for tag in tags:
				tags_elem.children.append(self._make_elem_base(
					'span',
					text=tag,
					classes='org-tag',
				))

			header.children.append(' ')
			header.children.append(tags_elem)

		return html

	@_convert_node.register('plain-list')
	def _convert_plain_list(self, node, ctx):
		if node['type'] == 'descriptive':
			return self._convert_dlist(node, ctx)
		else:
			return self._convert_uo_list(node, ctx)

	def _convert_uo_list(self, node, ctx):
		"""Convert ordered or unordered list."""
		listtype = node['type']

		if listtype == 'ordered':
			tag = 'ol'
		elif listtype == 'unordered':
			tag = 'ul'
		else:
			assert False

		html = self._make_elem_default(node, ctx, tag=tag)

		for item in node.contents:
			assert item.type == 'item'
			html.children.append(self._convert_uo_list_item(item, ctx))

		return html

	def _convert_uo_list_item(self, node, ctx):
		"""Convert ordered/unordered list item."""

		html = self._make_elem_default(node, ctx)

		# Checkbox state
		if node.props['checkbox']:
			html.add_class('org-checkbox org-checkbox-%s' % node.props['checkbox'])

		# If first child is a paragraph, extract its contents
		# (<p> tag inside <li> won't display correctly).
		contents = list(node.contents)

		if contents and get_node_type(contents[0]) == 'paragraph':
			contents = contents[0].contents + contents[1:]

		self._add_children(html, contents, ctx)

		return html

	def _convert_dlist(self, node, ctx):
		"""Convert a description list."""
		dlist = self._make_elem_default(node, ctx, tag='dl')

		for item in node.children:
			assert item.type == 'item'

			tag = self._make_elem_base('dt')
			self._add_children(tag, item['tag'], ctx)
			dlist.children.append(tag)

			data = self._convert_node_default(item, ctx, tag='dd')
			dlist.children.append(data)

		return dlist

	def _add_error(self, html, text=None):
		"""Add error state to a converted HTML element."""
		html.add_class('org-error')
		if text:
			html.attrs['title'] = text

	def _make_error_msg(self, msg, tag='div'):
		return self._make_elem_base(tag, text=msg, classes='org-error-msg')

	@_convert_node.register('entity')
	def _convert_entity(self, node, ctx):
		return node['utf-8']

	def _convert_link_default(self, node, ctx, url='#'):
		html = self._make_elem_default(node, ctx, classes='org-linktype-' + node['type'])

		# Add contents (these come from description part of link)
		if node.contents:
			self._add_children(html, node.contents, ctx)
		else:
			# No contents (no description), use raw-link
			html.children.append(node['raw-link'])
			html.add_class('org-link-raw')

		html.attrs['href'] = url
		return html

	@_convert_node.register('link')
	def _convert_link(self, node, ctx):
		linktype = node['type']

		if linktype in ('http', 'https'):
			return self._convert_link_default(node, ctx, url=node['path'])

		html = self._convert_link_default(node, ctx)
		self._add_error(html, text="Can't convert link %r!" % node['raw-link'])
		return html

	@_convert_node.register('code')
	def _convert_code(self, node, ctx):
		return self._make_elem_default(node, ctx, text=node['value'])

	@_convert_node.register('latex-fragment')
	def _convert_latex_fragment(self, node, ctx):
		value = node['value']

		import re
		match = re.fullmatch(r'(\$\$?|\\[[(])(.*?)(\$\$?|\\[\])])', value, re.S)
		d1, latex, d2 = match.groups()

		if d1 in ('$$', '\\['):
			d1, d2 = self.config['latex_delims']
			text = d1 + latex + d2

		elif d1 in ('$', '\\('):
			d1, d2 = self.config['latex_inline_delims']
			text = d1 + latex + d2

		else:
			assert False

		return text

	@_convert_node.register('src-block')
	def _convert_src_block(self, node, ctx):
		html = self._make_elem_default(node, ctx, tag='div')

		# Source code in "value" property
		code = self._make_elem_base('pre', text=node['value'], inline=True)
		code.add_class('org-src-block-value')
		html.children.append(code)

		# The contents are the results of executing the block?
		self._add_children(html, node.contents, ctx)

		return html

	@_convert_node.register('verbatim')
	@_convert_node.register('example-block')
	@_convert_node.register('statistics-cookie')
	@_convert_node.register('fixed-width')
	def _convert_node_with_value(self, node, ctx):
		"""Convert a node with "value" property that should be its text content."""
		value = node['value']
		assert isinstance(value, str)
		html = self._make_elem_default(node, ctx, text=value)
		return html

	@_convert_node.register('line-break')
	def _convert_line_break(self, node, ctx):
		return self._make_elem_base('br')

	@_convert_node.register('table')
	def _convert_table(self, node, ctx):
		# Divide rows into "blocks", separated by rule rows
		# These will be thead and tbody elements

		current_block = []
		blocks = [current_block]

		for row in node.contents:
			assert row.type == 'table-row'

			if row['type'] == 'rule':
				# New block
				current_block = []
				blocks.append(current_block)

			else:
				current_block.append(row.contents)

		# Now convert
		table_elem = self._make_elem_default(node, ctx, tag='table')

		for i, block in enumerate(blocks):
			# Interpret first block as header, unless its the only one
			is_head = i == 0 and len(blocks) > 1

			block_elem = self._make_elem_base('thead' if is_head else 'tbody')
			table_elem.children.append(block_elem)

			for row in block:
				row_elem = self._make_elem_base('tr')
				block_elem.children.append(row_elem)

				for cell in row:
					assert cell.type == 'table-cell'

					cell_elem = self._make_elem_base('th' if is_head else 'td')
					row_elem.children.append(cell_elem)

					self._add_children(cell_elem, cell.contents, ctx)

		return table_elem

	@_convert_node.register('timestamp')
	def _convert_timestamp(self, node, ctx):
		begin_str = node.begin.strftime(self.config['date_format'])

		html = self._make_elem_default(node, ctx)
		html.add_class('org-timestamp-%s' % node['type'])
		html.children.append(begin_str)

		return html

	@_convert_node.register('planning')
	def _convert_planning(self, node, ctx):
		html = self._make_elem_default(node, ctx, tag='table')

		for key in ['closed', 'scheduled', 'deadline']:
			if node[key] is not None:
				row = self._make_elem_base('tr')
				row.children.append(self._make_elem_base('th', text=key.title()))

				td = self._make_elem_base('td')
				td.children.append(self._convert(node[key], ctx))
				row.children.append(td)

				html.children.append(row)

		return html
