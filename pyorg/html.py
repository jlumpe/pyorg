"""Export org mode AST nodes to HTML."""

from collections import ChainMap
from xml.dom.minidom import Document

from .ast import ORG_ALL_OBJECTS


def add_class(elem, class_):
	"""Add class(es) to an HTML element.

	Parameters
	----------
	elem : xml.dom.minidom.Element
		Element to add class to.
	class_: str or list
		String or list of strings.
	"""
	if not isinstance(class_, str):
		class_ = ' '.join(class_)

	if 'class' in elem.attributes:
		elem.attributes['class'] = elem.attributes['class'].value + ' ' + class_
	else:
		elem.attributes['class'] = class_


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
	}

	DEFAULT_CONFIG = {
		'latex_delims': ('$$', '$$'),
		'latex_inline_delims': (r'\(', r'\)'),
	}

	def __init__(self, config=None, **kw):
		self.doc = Document()

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

	def convert(self, what):
		return self._convert(what, None)

	def _convert(self, what, ctx):
		"""Convert an org AST node OR text to HTML element."""
		if isinstance(what, str):
			return self.doc.createTextNode(what)
		else:
			return self._convert_node(what, ctx)

	def _convert_node_default(self, node, ctx, **kwargs):
		html = self._make_elem(node, ctx, **kwargs)
		self._add_children(html, node.contents, ctx)
		return html

	_convert_node = dispatch_node_type()(_convert_node_default)
	_convert_node.__doc__ = """Recursively _convert an org AST node to HTML."""

	def _make_elem_base(self, tag, text=None, attrs=None, classes=None):
		"""Create a new HTML element."""
		html = self.doc.createElement(tag)
		if text is not None:
			html.appendChild(self.doc.createTextNode(text))
		if attrs is not None:
			for key, value in attrs.items():
				html.attributes[key] = value
		if classes is not None:
			if not isinstance(classes, str):
				classes = ' '.join(classes)
			html.attributes['class'] = classes
		return html

	def _make_elem_default(self, node, ctx, tag=None, **kwargs):
		no_default = False

		if tag is None:
			tag = self.default_tag(node.type)
			if node.type not in self.TAGS:
				no_default = True

			if tag is None:
				return None

		html = self._make_elem_base(tag, **kwargs)
		add_class(html, 'org-node org-%s' % node.type)

		# Warn about no default tag
		if no_default:
			msg = "Don't know how to convert node of type %r" % node.type
			self._add_error(html)
			html.appendChild(self._make_error_msg(msg))

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
				parent.appendChild(html)

	@_make_elem.register('headline')
	def _make_headline(self, node, ctx):
		level = node['level']

		if not (1 <= level <= 5):
			raise NotImplementedError()

		html = self.doc.createElement('div')
		html.attributes['class'] = 'org-header-container org-header-level-%d' % level

		header = self._make_elem_default(node, ctx, tag='h%d' % (level + 1))
		html.appendChild(header)

		# TODO info
		todo_type = node.props['todo-type']

		if todo_type:
			todo_kw = node.props['todo-keyword']

			add_class(html, 'org-has-todo')
			add_class(html, 'org-todo-%s' % todo_type)
			add_class(html, 'org-todo-kw-%s' % todo_kw)

			header.appendChild(self._make_elem_base(
				'span',
				text=todo_kw,
				classes='org-todo org-todo-%s' % todo_type,
			))

			priority_code = node.props['priority']

			if priority_code is not None:
				priority_char = chr(priority_code)
				header.appendChild(self._make_elem_base(
					'span',
					text=priority_char,
					classes='org-todo-priority org-todo-priority-%s' % priority_char,
				))

		# Text
		header_text = self._make_elem_base('span', classes='org-header-text')
		self._add_children(header_text, node['title'], ctx)
		header.appendChild(header_text)

		# Tags
		tags = node.props['tags']
		if tags:
			tags_elem = self._make_elem_base('span', classes='org-tags')

			for tag in tags:
				tags_elem.appendChild(self._make_elem_base(
					'span',
					text=tag,
					classes='org-tag',
				))

			header.appendChild(tags_elem)

		return html

	@_convert_node.register('plain-list')
	def _convert_plain_list(self, node, ctx):
		listtype = node['type']

		if listtype == 'ordered':
			tag = 'ol'
		elif listtype == 'unordered':
			tag = 'ul'
		elif listtype == 'descriptive':
			return self._convert_dlist(node, ctx)
		else:
			assert False

		return self._convert_node_default(node, ctx, tag=tag)

	def _convert_dlist(self, node, ctx):
		"""Convert a description list."""
		dlist = self._make_elem_default(node, ctx, tag='dl')

		for item in node.children:
			assert item.type == 'item'

			tag = self._make_elem_base('dt')
			self._add_children(tag, item['tag'], ctx)
			dlist.appendChild(tag)

			data = self._convert_node_default(item, ctx, tag='dd')
			dlist.appendChild(data)

		return dlist

	def _add_error(self, html, text=None):
		"""Add error state to a converted HTML element."""
		add_class(html, 'org-error')
		if text:
			html.attributes['title'] = text

	def _make_error_msg(self, msg, tag='div'):
		return self._make_elem_base(tag, text=msg, classes='org-error-msg')

	@_convert_node.register('entity')
	def _convert_entity(self, node, ctx):
		return self.doc.createTextNode(node['utf-8'])

	def _convert_link_default(self, node, ctx, url='#'):
		html = self._make_elem_default(node, ctx)

		# Add contents (these come from description part of link)
		if node.contents:
			self._add_children(html, node.contents, ctx)
		else:
			# No contents (no description), use raw-link
			html.appendChild(self.doc.createTextNode(node['raw-link']))
			add_class(html, 'org-link-raw')

		html.attributes['href'] = url
		return html

	@_convert_node.register('link')
	def _convert_link(self, node, ctx):
		linktype = node['type']

		if linktype in ('http', 'https'):
			return self._convert_link_default(node, ctx, url=node['path'])

		html = self._convert_link_default(node, ctx)
		self._add_error(html, text="Can't convert link of type %r!" % linktype)
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

		return self.doc.createTextNode(text)

	@_convert_node.register('src-block')
	def _convert_src_block(self, node, ctx):
		html = self._make_elem_default(node, ctx, tag='div')

		# Source code in "value" property
		code = self._make_elem_base('pre', text=node['value'])
		add_class(code, 'org-src-block-value')
		html.appendChild(code)

		# The contents are the results of executing the block?
		self._add_children(html, node.contents, ctx)

		return html

	@_convert_node.register('verbatim')
	@_convert_node.register('example-block')
	def _convert_node_with_value(self, node, ctx):
		"""Convert a node with "value" property that should be its text content."""
		value = node.props['value']
		assert isinstance(value, str)
		html = self._make_elem_default(node, ctx)
		html.appendChild(self.doc.createTextNode(value))
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

			if row.props['type'] == 'rule':
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
			table_elem.appendChild(block_elem)

			for row in block:
				row_elem = self._make_elem_base('tr')
				block_elem.appendChild(row_elem)

				for cell in row:
					assert cell.type == 'table-cell'

					cell_elem = self._make_elem_base('th' if is_head else 'td')
					row_elem.appendChild(cell_elem)

					self._add_children(cell_elem, cell.contents, ctx)

		return table_elem
