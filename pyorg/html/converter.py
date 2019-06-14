from collections import ChainMap
import re
from pathlib import Path

from pyorg.ast import ORG_NODE_TYPES, get_node_type, as_node_type, dispatch_node_type
from .element import HtmlElement, TextNode


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
		'fixed-width': 'pre',
		'babel-call': None,
		'horizontal-rule': 'hr',
		'radio-target': 'span',  # TODO
		'property-drawer': None,
	}

	INLINE_NODES = frozenset(
		{'paragraph', 'example-block', 'fixed-width'}
		| {nt.name for nt in ORG_NODE_TYPES.values() if nt.is_object}
	)

	DEFAULT_CONFIG = {
		'latex_delims': ('$$', '$$'),
		'latex_inline_delims': (r'\(', r'\)'),
		'date_format': '%Y-%m-%d %a',
		'resolve_link': {},
		'image_extensions': ('.png', '.jpg', '.gif', '.tiff'),
	}

	DEFAULT_RESOLVE_LINK = {
		'http': True,
		'https': True,
	}

	def __init__(self, config=None, **kw):
		if config is None:
			config = {}
		if kw:
			config = {**config, **kw}
		self.config = ChainMap(config, self.DEFAULT_CONFIG)

	def default_tag(self, type_):
		type_ = as_node_type(type_)
		try:
			return self.TAGS[type_.name]
		except KeyError:
			return 'span' if type_.is_object else 'div'

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
		if html is not None:
			self._add_children(html, node.contents, ctx)
		return html

	_convert_node = dispatch_node_type()(_convert_node_default)
	_convert_node.__doc__ = """Recursively _convert an org AST node to HTML."""

	def _make_elem_base(self, tag, text=None, classes=None, **kwargs):
		"""Create a new HTML element."""
		html = HtmlElement(tag, **kwargs)
		if text is not None:
			html.children.append(text)
		if classes is not None:
			html.classes = classes
		return html

	def _make_elem_default(self, node, ctx, tag=None, **kwargs):
		no_default = False

		if tag is None:
			tag = self.default_tag(node.type.name)
			if node.type.name not in self.TAGS:
				no_default = True

			if tag is None:
				return None

		if node.type.name in self.INLINE_NODES:
			kwargs.setdefault('inline', True)
			kwargs.setdefault('post_ws', node.props.get('post-blank', 0) > 0)

		html = self._make_elem_base(tag, **kwargs)
		html.add_class('org-node org-%s' % node.type.name)

		# Warn about no default tag
		if no_default:
			msg = "Don't know how to convert node of type %r" % node.type.name
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

	def _make_text(self, node, text, ct):
		"""Creates plain text from org node.

		Takes care of adding whitespace after if needed.
		"""
		return TextNode(text, post_ws=node.props.get('post-blank', 0) > 0)

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
				post_ws=True,
			))

			priority_code = node.props['priority']

			if priority_code is not None:
				priority_char = chr(priority_code)
				header.children.append(self._make_elem_base(
					'span',
					text=priority_char,
					classes='org-todo-priority org-todo-priority-%s' % priority_char,
					post_ws=True,
				))

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
					post_ws=True,
				))

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
			assert item.type.name == 'item'
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
			assert item.type.name == 'item'

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
		return self._make_text(node, node['utf-8'], ctx)

	def _convert_link_default(self, node, ctx, url=None):
		html = self._make_elem_default(node, ctx, classes='org-linktype-' + node['type'])

		# Add contents (these come from description part of link)
		if node.contents:
			self._add_children(html, node.contents, ctx)
		else:
			# No contents (no description), use raw-link
			html.children.append(node['raw-link'])
			html.add_class('org-link-raw')

		if url is not None:
			html.attrs['href'] = url

		return html

	@_convert_node.register('link')
	def _convert_link(self, node, ctx):
		url = self.resolve_link(node['type'], node['raw-link'], node['path'])

		if url and node['type'] == 'file':
			return self._convert_file_link(node, ctx, url)

		if url:
			html = self._convert_link_default(node, ctx, url=url)
		else:
			html = self._convert_link_default(node, ctx)
			self._add_error(html, text="Can't convert link %r!" % node['raw-link'])

		return html

	def _convert_file_link(self, node, ctx, url):
		path = Path(node['path'])

		if path.suffix in self.config['image_extensions'] and not node.contents:
			return self._convert_image(node, ctx, url)

		return self._convert_link_default(node, ctx, url)

	def _convert_image(self, node, ctx, url):
		html = self._make_elem_default(node, ctx, classes='org-img-link', tag='img')
		html.attrs['src'] = url
		html.attrs['title'] = node['path']
		return html

	def resolve_link(self, linktype, raw, path, ctx=None):
		"""Resolve link into a proper URL."""
		resolve_link = ChainMap(self.config.get('resolve_link', {}), self.DEFAULT_RESOLVE_LINK)
		resolve = resolve_link.get(linktype)

		if resolve is None or resolve is False:
			return None

		if resolve is True:
			return raw

		if not callable(resolve):
			raise TypeError('resolve_link value must be None, bool or callable')

		return resolve(linktype, raw, path)

	@_convert_node.register('code')
	def _convert_code(self, node, ctx):
		return self._make_elem_default(node, ctx, text=node['value'])

	@_convert_node.register('latex-fragment')
	def _convert_latex_fragment(self, node, ctx):
		value = node['value']

		# Remove delimiters, if any
		match = re.fullmatch(r'(\$\$?|\\[[(])(.*?)(\$\$?|\\[\])])', value, re.S)
		if match:
			d1, latex, d2 = match.groups()
			inline = d1 in ('$', '\\(')
		else:
			latex = value
			inline = True

		d1, d2 = self.config['latex_inline_delims' if inline else 'latex_delims']
		return self._make_text(d1 + latex + d2)

	@_convert_node.register('src-block')
	def _convert_src_block(self, node, ctx):
		params = node.props.get('parameters', {})
		print('params = %r' % params)

		export = params.get('export', 'both')
		export_code = export in ('code', 'both')
		export_results = export in ('results', 'both')

		if not export_code and not export_results:
			return None

		html = self._make_elem_default(node, ctx, tag='div')

		# Source code in "value" property
		if export_code:
			code = self._make_elem_base('pre', text=node['value'], inline=True)
			code.add_class('org-src-block-value')
			html.children.append(code)

		# The contents are the results of executing the block?
		if export_results:
			self._add_children(html, node.contents, ctx)

		return html

	@_convert_node.register(['verbatim', 'example-block', 'statistics-cookie', 'fixed-width'])
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
			assert row.type.name == 'table-row'

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
					assert cell.type.name == 'table-cell'

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
