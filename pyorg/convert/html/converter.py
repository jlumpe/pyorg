from collections import ChainMap
import re
from pathlib import Path

from pyorg.ast import OrgNode, OrgTimestamp, ORG_NODE_TYPES, get_node_type, as_node_type, dispatch_node_type
from pyorg.util import SingleDispatch
from .element import HtmlElement, TextNode
from pyorg.convert.base import OrgConverterBase


class OrgHtmlConverter(OrgConverterBase):

	# Default HTML tag for each node type. None means to skip.
	TAGS = {
		'org-data': 'article',
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
		'section': 'section',
		'headline': 'article',
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
		'keyword': None
	}

	INLINE_NODES = frozenset(
		{'paragraph', 'example-block', 'fixed-width'}
		| {nt.name for nt in ORG_NODE_TYPES.values() if nt.is_object}
	)

	DEFAULT_CONFIG = {
		'latex_delims': ('$$', '$$'),
		'latex_inline_delims': (r'\(', r'\)'),
		'resolve_link': {},
		**OrgConverterBase.DEFAULT_CONFIG
	}

	DEFAULT_RESOLVE_LINK = {
		'http': True,
		'https': True,
	}

	def default_tag(self, type_):
		type_ = as_node_type(type_)
		try:
			return self.TAGS[type_.name]
		except KeyError:
			return 'span' if type_.is_object else 'div'

	def default_classes(self, type):
		return ['org-node', 'org-' + type.name]

	def convert(self, node, dom=False, **kwargs):
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
		elem = super().convert(node, **kwargs)

		if dom:
			return elem

		return str(elem)

	@SingleDispatch
	def _convert(self, what, ctx):
		"""Convert an org AST node OR text to HTML element."""
		raise TypeError("Can't convert object of type %r" % type(what))

	@_convert.register(str)
	def _convert_string(self, string, ctx):
		return TextNode(string)

	@_convert.register(OrgNode)
	@dispatch_node_type()
	def _convert_node(self, node, ctx, **kwargs):
		"""Recursively _convert an org AST node to HTML."""
		html = self._make_elem(node, ctx, **kwargs)
		if html is not None:
			self._add_children(html, node.contents, ctx)
		return html

	def _make_elem_base(self, tag, text=None, classes=None, **kwargs):
		"""Create a new HTML element."""
		html = HtmlElement(tag, **kwargs)
		if text is not None:
			html.children.append(text)
		if classes is not None:
			html.classes = classes
		return html

	@dispatch_node_type()
	def _make_elem(self, node, ctx, tag=None, **kwargs):
		"""
		Make the HTML element for a given org node (but do not recurse to
		children).
		"""
		no_default = False

		if tag is None:
			tag = self.default_tag(node.type.name)
			if node.type.name not in self.TAGS:
				no_default = True

			if tag is None:
				return None

		if node.type.name in self.INLINE_NODES:
			kwargs.setdefault('inline', True)
			kwargs.setdefault('post_ws', node.properties.get('post-blank', 0) > 0)

		html = self._make_elem_base(tag, **kwargs)
		html.add_class(self.default_classes(node.type))

		# Warn about no default tag
		if no_default:
			msg = "Don't know how to convert node of type %r" % node.type.name
			self._add_error(html)
			html.children.append(self._make_error_msg(msg))

		return html

	def _add_children(self, parent, org_nodes, ctx):
		"""Recursively _convert org AST nodes and add to parent html element."""
		for i, node in enumerate(org_nodes):
			html = self._convert(node, ctx._push(i))
			if html is not None:
				parent.children.append(html)

	def _make_text(self, node, text, ctx):
		"""Create plain text from org node.

		Takes care of adding whitespace after if needed.
		"""
		return TextNode(text, post_ws=node.properties.get('post-blank', 0) > 0)

	def make_headline_text(self, node, ctx=None, dom=False):
		"""Make HTML element for text content of headline node."""
		if ctx is None:
			ctx = self._init_ctx(node, {})
		elem = self._make_elem_base('span', classes='org-header-text')
		self._add_children(elem, node['title'], ctx)

		if dom:
			return elem

		return str(elem)

	@_make_elem.register('org-data')
	def _make_org_data(self, node, ctx):
		elem = self._make_elem.default(node, ctx)

		title = ctx.kwargs.get('title', True)
		if title is True:
			title = node.title

		if title:
			assert isinstance(title, str)
			elem.children.append(self._make_elem_base('h1', text=title, classes='org-data-title'))

		return elem

	def _make_headline(self, headline, ctx):
		"""
		Make the HTML element for the headline itself, without section or subheadings.
		"""
		tag = 'h%d' % min(headline.level + 1, 6)
		header = self._make_elem.default(headline, ctx, tag=tag, inline=True)

		# TODO info
		if headline['todo-type']:
			todo = self._make_todo(headline, ctx)
			header.children.append(todo)

		# Text
		header_text = self.make_headline_text(headline, ctx, dom=True)
		header.children.append(header_text)

		# Tags
		if headline['tags']:
			tags = self._make_headline_tags(headline, ctx)
			header.children.append(tags)

		return header

	def _make_todo(self, headline, ctx):
		"""Make the element for a headline's TODO."""
		todo = self._make_elem_base('span', classes='org-todo')

		todo.children.append(self._make_elem_base(
			'span',
			text=headline['todo-keyword'],
			classes=[
				'org-todo-kw',
				'org-todo-' + headline['todo-type'],
				'org-todo-kw-' + headline['todo-keyword'],
			],
			post_ws=True,
		))

		if headline['priority'] is not None:
			todo.children.append(self._make_elem_base(
				'span',
				text=headline.priority_chr,
				classes='org-todo-priority org-priority-' + headline.priority_chr,
				post_ws=True,
			))

		return todo

	def _make_headline_tags(self, headline, ctx):
		"""Make the element for the headline's tags."""
		elem = self._make_elem_base('span', classes='org-tags')

		for tag in headline['tags']:
			elem.children.append(self._make_elem_base(
				'span',
				text=tag,
				classes='org-tag',
				post_ws=True,
			))
		return elem

	def _make_headline_planning(self, headline, ctx):
		"""Convert planning data for headline."""

		rows = []

		for key in ['closed', 'scheduled', 'deadline']:
			if headline.properties.get(key) is not None:
				row = self._make_elem_base('tr')
				row.children.append(self._make_elem_base('th', text=key.title()))

				td = self._make_elem_base('td')
				td.children.append(self._convert(headline[key], ctx._push(key)))
				row.children.append(td)

				rows.append(row)

		if rows:
			html = self._make_elem_base(tag='table', classes='org-planning')
			html.children.extend(rows)

			return html

		return None

	@_make_elem.register('headline')
	def _make_headline_outer(self, node, ctx):
		"""Make the outer container for a headline node.

		Includes headline HTML element itself, plus section and subheaders.
		"""
		assert node.is_outline

		html = HtmlElement('div')
		html.classes = 'org-header-container org-header-level-%d' % node.level

		# ID
		if node.id:
			html.attrs['id'] = node.id

		# Header element
		header = self._make_headline(node, ctx)
		html.children.append(header)

		# Planning
		planning = self._make_headline_planning(node, ctx)
		if planning:
			html.children.append(planning)

		# Add classes for TODO info
		if node.has_todo:
			html.add_class('org-has-todo')
			html.add_class('org-todo-%s' % node['todo-type'])
			html.add_class('org-todo-kw-%s' % node['todo-keyword'])

			if node.priority_chr:
				html.add_class('org-priority-' + node.priority_chr)

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

		html = self._make_elem.default(node, ctx, tag=tag)

		for i, item in enumerate(node.contents):
			assert item.type.name == 'item'
			html.children.append(self._convert_uo_list_item(item, ctx._push(i)))

		return html

	def _convert_uo_list_item(self, node, ctx):
		"""Convert ordered/unordered list item."""

		html = self._make_elem.default(node, ctx)

		# Checkbox state
		if node['checkbox']:
			html.add_class('org-has-checkbox org-checkbox-%s' % node['checkbox'])

			input = self._make_elem_base(
				'input',
				classes='org-checkbox',
				attrs=dict(
					type='checkbox',
					disabled=True,
					checked=node['checkbox'] == 'on',
				)
			)
			html.children.append(input)

		# If first child is a paragraph, extract its contents
		# (<p> tag inside <li> won't display correctly).
		contents = list(node.contents)

		if contents and get_node_type(contents[0]) == 'paragraph':
			contents = contents[0].contents + contents[1:]

		self._add_children(html, contents, ctx)

		return html

	def _convert_dlist(self, node, ctx):
		"""Convert a description list."""
		dlist = self._make_elem.default(node, ctx, tag='dl')

		for i, item in enumerate(node.children):
			assert item.type.name == 'item'

			ctxi = ctx._push(i)

			tag = self._make_elem_base('dt')
			self._add_children(tag, item['tag'], ctxi)
			dlist.children.append(tag)

			data = self._convert_node.default(item, ctxi, tag='dd')
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
		html = self._make_elem.default(node, ctx, classes='org-linktype-' + node['type'])

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
		html = self._make_elem.default(node, ctx, classes='org-img-link', tag='img')
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
		return self._make_elem.default(node, ctx, text=node['value'])

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
		text = d1 + latex + d2
		return self._make_text(node, text, ctx)

	@_convert_node.register('src-block')
	def _convert_src_block(self, node, ctx):
		# params = node.properties.get('parameters', {'export': 'both'})
		params = {'export': 'both'}

		export = params.get('export', 'both')
		export_code = export in ('code', 'both')
		export_results = export in ('results', 'both')

		if not export_code and not export_results:
			return None

		html = self._make_elem.default(node, ctx, tag='div')

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
		return self._make_elem.default(node, ctx, text=value)

	@_convert_node.register('line-break')
	def _convert_line_break(self, node, ctx):
		return self._make_elem_base('br')

	@_convert_node.register('table')
	def _convert_table(self, node, ctx):
		table_elem = self._make_elem.default(node, ctx, tag='table')

		blocks = node.blocks()
		for i, block in enumerate(blocks):
			# Interpret first block as header, unless its the only one
			is_head = i == 0 and len(blocks) > 1

			block_elem = self._make_elem_base('thead' if is_head else 'tbody')
			table_elem.children.append(block_elem)

			for row in block:
				row_elem = self._convert_table_row(row, ctx, is_head)
				block_elem.children.append(row_elem)

		return table_elem

	def _convert_table_row(self, node, ctx, header=False):
		row_elem = self._make_elem_base('tr')

		for i, cell in enumerate(node):
			assert cell.type.name == 'table-cell'

			cell_elem = self._make_elem_base('th' if header else 'td')
			row_elem.children.append(cell_elem)

			self._add_children(cell_elem, cell.contents, ctx._push(i))

		return row_elem

	@_convert.register(OrgTimestamp)
	@_convert_node.register('timestamp')
	def _convert_timestamp(self, ts, ctx):

		html = self._make_elem_base('span', classes='org-timestamp')

		if ts.tstype in ('active', 'active-range'):
			html.add_class('org-timestamp-active')
		elif ts.tstype in ('inactive', 'inactive-range'):
			html.add_class('org-timestamp-inactive')
		else:
			html.add_class('org-timestamp-' + ts.tstype)

		fmt = self.config['date_format']

		if ts.is_range:
			html.add_class('org-timestamp-range')
			start = ts.start.strftime(fmt)
			end = ts.end.strftime(fmt)
			html.children.append('%s to %s' % (start, end))

		else:
			html.children.append((ts.start or ts.end).strftime(fmt))

		return html


def to_html(node, dom=False, **kwargs):
	"""Convert org node to HTML.

	Parameters
	---------
	node : pyorg.ast.OrgNode
		Org node to convert.
	dom : bool
		Return HTML element instead of string.
	kwargs
		Keyword arguments to :class:`.OrgHtmlConverter` constructor.

	Returns
	-------
	str or HtmlElement
	"""
	converter = OrgHtmlConverter(**kwargs)
	return converter.convert(node, dom=dom)
