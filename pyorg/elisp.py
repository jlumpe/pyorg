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


def switch_to_file_buffer(emacs, file, focus=False):
	"""Get or create a buffer visiting a file and display it.

	Uses an existing buffer visiting the file if possible, otherwise
	creates one. If this buffer is already displayed in some window
	select it, otherwise open it in a new window (where?). The window
	(and its frame, if different than the current one) are then given
	focus.

	Parameters
	----------
	emacs : emacs.emacs.Emacs
	file : str
		Absolute path to file to open.
	focus : bool
		Switch window system focus to the active Emacs frame.

	Raises
	------
	emacs.emacs.EmacsException
	"""
	form = E.pyorg_switch_to_file_buffer(str(file), bool(focus))
	emacs.eval(form)


def goto_headline(emacs, ids, focus=True):
	"""Open/display an org file in Emacs and move to a specific headline.

	Arguments may be given either as keyword arguments or within a dictionary
	passed as ``ids``. A value for ``file`` is required unless ``id`` is given.

	Parameters
	----------
	emacs : emacs.emacs.Emacs
	ids : dict
		Dictionary in the same format as returned by
		:func:`pyorg.outline.headline_identifiers`. May have the following
		keys:
		* ``'file'`` (``str``) - Absolute path to the file the headline resides in.
		* ``'id'`` (``str``) - The headline's ``ID`` property.
		* ``'custom_id'`` (``str``) - The headline's ``CUSTOM_ID`` property.
		* ``'text'`` (``str``) - The exact text contained in the headline,
		  excluding leading asterisks, TODO keyword, and tags.
		* ``'position'`` (``int``) - Position of headline within file.
	focus : bool
		Give the active Emacs frame focus from the OS' window system.

	Returns
	-------
	bool
		True if the headline was found, False otherwise.

	Raises
	------
	emacs.emacs.EmacsException
	"""

	kw = {
		key: ids[key]
		for key in ['file', 'id', 'custom_id', 'text', 'position']
		if key in ids
	}

	file = kw.pop('file', None)
	if file is None and kw.get('id') is None:
		raise TypeError('At least one of "file" or "id" is required.')

	form = E['if'](E.pyorg_goto_headline(file, focus=focus, **kw), E.t)
	output = emacs.eval(form)

	if output == 't':
		return True
	if output == 'nil':
		return False

	raise RuntimeError('Unexpected Emacs output: %r' % output)
