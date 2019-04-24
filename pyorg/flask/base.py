from flask import current_app, g
from werkzeug.local import LocalProxy


def get_emacs():
	"""Get ``EmacsInterface`` instance to use with application context.

	Returns
	-------
	pyorg.emacs.EmacsInterface
	"""
	if 'emacs' not in g:
		from pyorg.emacs import EmacsInterface

		g.emacs = EmacsInterface(
			cmd=current_app.config.get('PYORG_EMACS_CMD'),
			client=current_app.config.get('PYORG_EMACS_IS_CLIENT', False),
		)

	return g.emacs


def get_org_interface():
	"""Get ``OrgInterface`` instance to use with application context.

	Returns
	-------
	pyorg.emacs.OrgInterface
	"""
	if 'orginterface' not in g:
		from pyorg.interface import OrgInterface

		g.orginterface = OrgInterface(
			emacs=get_emacs(),
			orgdir=current_app.config.get('PYORG_ORG_DIRECTORY')
		)

	return g.orginterface


emacs = LocalProxy(get_emacs)
orginterface = LocalProxy(get_org_interface)
