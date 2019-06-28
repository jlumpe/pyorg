from .ast import as_secondary_string
from .convert.plaintext import to_plaintext


class OrgAgendaItem:
	"""An agenda item.

	Attributes
	----------
	text : list
		Main text of the item, as secondary string.
	text_plain : str
		Text as simple string.
	type : str
		TODO type.
	keyword : str
		TODO keyword.
	headline : OrgAstNode
		Headline node item came from.
	headline_path : list
		Titles of headline and its ancestors.
	file : str
		File todo is located in, relative to org-directory
	deadline : OrgAstNode
		timestamp node
	priority : str
		Priority letter assigned to the item's headline.
	priority_code : int
		Character code for priority.
	view_priority : int
		Relative priority assigned to the item in the agenda buffer it was exported
		from.
	tags : list
		List of tags.
	extra : dict
		Extra data.
	"""
	__attrs__ = [
		'type',
		'keyword',
		'headline',
		'headline_path',
		'file',
		'deadline',
		'view_priority',
		'tags',
	]
	__attr_defaults__ = {
		'tags': [],
		'view_priority': 0,
	}

	def __init__(self, text, **kwargs):
		self.text = as_secondary_string(text)
		self.text_plain = kwargs.pop('text_plain')
		if self.text_plain is None:
			self.text_plain = to_plaintext(self.text)

		for name in self.__attrs__:
			value = kwargs.pop(name, self.__attr_defaults__.get(name))
			setattr(self, name, value)

		priority = kwargs.pop('priority', None)
		if isinstance(priority, int):
			self.priority = chr(priority)
		elif (isinstance(priority, str) and len(priority) == 1) or priority is None:
			self.priority = priority
		else:
			raise ValueError('Priority should be a single character or a character code')

		self.extra = kwargs

	@property
	def priority_code(self):
		return None if self.priority is None else ord(self.priority)

	@priority_code.setter
	def priority_code(self, value):
		self.priority = None if value is None else chr(value)
