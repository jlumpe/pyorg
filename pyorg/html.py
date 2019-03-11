"""Export org mode AST elements to HTML."""

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
		elem.attributes['class'] += ' ' + class_
	else:
		elem.attributes['class'] = class_


class DispatchEltype:

	def __init__(self, default, registry=None, instance=None):
		self.default = default
		self.registry = {} if registry is None else registry
		self.instance = instance

	def bind(self, instance):
		return DispatchEltype(self.default, self.registry, instance)

	def unbind(self):
		return DispatchEltype(self.default, self.registry, None)

	def __get__(self, instance, owner):
		if instance is None:
			return self
		return self.bind(instance)

	def dispatch(self, eltype):
		method = self.registry.get(eltype, self.default)
		if self.instance is not None:
			method.__get__(self.instance, type(self.instance))
		return method

	def register(self, eltype):
		def decorator(method):
			self.registry[eltype] = method
			return method

		return decorator

	def __call__(self, *args, **kwargs):
		if self.instance is not None:
			return self._call(self.instance, *args, **kwargs)
		return self._call(*args, **kwargs)

	def _call(self, instance, element, *args, **kwargs):
		method = self.dispatch(element.type)
		return method(instance, element, *args, **kwargs)


def dispatch_eltype(parent=None):
	registry = {} if parent is None else ChainMap(parent, {})

	def decorator(default):
		return DispatchEltype(default, registry)

	return decorator


class OrgHtmlConverter:

	TAGS = {
		'item': 'li',
		'paragraph': 'p',
		'bold': 'strong',
		'code': 'code',
		'example-block': 'pre',
		'italic': 'em',
		'link': 'a',
		'src-block': 'pre',
		'strike-through': 's',
		'superscript': 'sup',
		'subscript': 'sub',
		'underline': 'u',
	}

	config = {
		'latex_delims': ('$$', '$$'),
		'latex_inline_delims': (r'\(', r'\)'),
	}

	def __init__(self):
		self.doc = Document()

	def default_tag(self, eltype):
		try:
			return self.TAGS[eltype]
		except KeyError:
			return 'span' if eltype in ORG_ALL_OBJECTS else 'div'

	def convert(self, what):
		return self._convert(what, None)

	def _convert(self, what, ctx):
		"""Convert an org element OR text to HTML element."""
		if isinstance(what, str):
			return self.doc.createTextNode(what)
		else:
			return self._convert_elem(what, ctx)

	def _convert_elem_default(self, orgelem, ctx, **kwargs):
		html = self._make_elem(orgelem, ctx, **kwargs)
		self._add_children(html, orgelem.contents, ctx)
		return html

	_convert_elem = dispatch_eltype()(_convert_elem_default)
	_convert_elem.__doc__ = """Recursively _convert an org element to HTML."""

	def _make_elem_base(self, tag, text=None, attrs=None):
		"""Create a new HTML element."""
		html = self.doc.createElement(tag)
		if text is not None:
			html.appendChild(self.doc.createTextNode(text))
		if attrs is not None:
			html.attributes.update(attrs)
		return html

	def _make_elem_default(self, orgelem, ctx, tag=None, **kwargs):
		if tag is None:
			tag = self.default_tag(orgelem.type)

		html = self._make_elem_base(tag, **kwargs)
		add_class(html, 'org-element org-eltype-%s' % orgelem.type)

		return html

	_make_elem = dispatch_eltype()(_make_elem_default)
	_make_elem.__doc__ = """
	Make the HTML element for a given org element (but do not recurse to
	children).
	"""

	def _add_children(self, parent, org_elems, ctx):
		"""Recursively _convert org elements and add to parent html element."""
		for oelem in org_elems:
			html = self._convert(oelem, ctx)
			parent.appendChild(html)

	@_make_elem.register('headline')
	def _make_headline(self, elem, ctx):
		level = elem['level']

		if not (1 <= level <= 5):
			raise NotImplementedError()

		html = self.doc.createElement('div')
		html.attributes['class'] = 'org-header-container org-header-level-%d' % level

		header = self._make_elem_default(elem, ctx, tag='h%d' % (level + 1))
		self._add_children(header, elem['title'], ctx)

		html.appendChild(header)

		return html

	@_convert_elem.register('plain-list')
	def _convert_plain_list(self, orgelem, ctx):
		listtype = orgelem['type']

		if listtype == 'ordered':
			tag = 'ol'
		elif listtype == 'unordered':
			tag = 'ul'
		elif listtype == 'descriptive':
			return self._convert_dlist(orgelem, ctx)
		else:
			assert False

		return self._convert_elem_default(orgelem, ctx, tag=tag)

	def _convert_dlist(self, orgelem, ctx):
		"""Convert a description list."""
		dlist = self._make_elem_default(orgelem, ctx, tag='dl')

		for item in orgelem.children:
			assert item.type == 'item'

			tag = self._make_elem_base('dt')
			self._add_children(tag, item['tag'], ctx)
			dlist.appendChild(tag)

			data = self._convert_elem_default(item, ctx, tag='dd')
			dlist.appendChild(data)

		return dlist

	@_convert_elem.register('entity')
	def _convert_entity(self, orgelem, ctx):
		return self.doc.createTextNode(orgelem['utf-8'])

	@_convert_elem.register('link')
	def _convert_link(self, orgelem, ctx):
		linktype = orgelem['type']

		if linktype in ('http', 'https'):
			html = self._convert_elem_default(orgelem, ctx)
			html.attributes['href'] = orgelem['path']
			return html

		if linktype == 'file':
			return self._convert_file_link(orgelem, ctx)

		return self._convert_elem_default(orgelem, ctx, tag='span',
			text='Cant convert link of type %r!' % linktype)

		raise NotImplementedError()

	def _convert_file_link(self, link, ctx):
		html = self._convert_elem_default(link, ctx)
		html.attributes['href'] = '#'
		return html

	@_convert_elem.register('code')
	def _convert_code(self, orgelem, ctx):
		return self._make_elem_default(orgelem, ctx, text=orgelem['value'])

	@_convert_elem.register('latex-fragment')
	def _convert_latex_fragment(self, orgelem, ctx):
		value = orgelem['value']

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
