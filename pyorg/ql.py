"""Tools for using the org-ql Emacs package."""

import emacs.elisp as el
from emacs.elisp import E

from .interface import OrgPlugin
from .io import org_node_from_json


ORG_QL_TODO_BASE_QUERY = E.Q(E['and'](E.todo(), E['not'](E.done())))



class OrgQlPlugin(OrgPlugin):
	api_name = 'ql'

	def _init(self):
		self.org.emacs.eval(E.require(E.Q('org-ql')))

	def select(self, query=None, files=None, todo=False):
		if files:
			files = el.List(list(map(str, files)))
		else:
			files = E.org_agenda_files

		if todo:
			query = ORG_QL_TODO_BASE_QUERY

		src = E.ox_json_ql_select(files, query)

		data = self.org.emacs.getresult(src, is_json=True)

		return list(map(org_node_from_json, data))
