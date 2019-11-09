"""Python function wrappers for Elisp code."""

import os

import emacs.elisp as el
from emacs.elisp import E


def export_org_file_el(file, dest):
	"""Create elisp code to export org file as JSON.

	Parameters
	----------
	file : str
		Absolute path to org file to be exported.
	dest : str
		Absolute path to write exported data to.

	Returns
	-------
	emacs.elisp.Form
	"""
	return E.pyorg_export_org_file(str(file), str(dest))


def export_org_file(emacs, file, dest):
	"""Export an org file as JSON.

	Parameters
	----------
	emacs : emacs.Emacs
		Emacs interface object.
	file : str
		Absolute path to org file to be exported.
	dest : str
		Absolute path to write exported data to.

	Raises
	------
	FileNotFoundError
		If ``file`` does not exist.
	"""
	if not os.path.isabs(file) or not os.path.isabs(dest):
		raise ValueError('"file" and "dest" paths must be absolute.')
	if not os.path.isfile(file):
		raise FileNotFoundError(file)
	form = export_org_file_el(file, dest)
	emacs.eval(form)

