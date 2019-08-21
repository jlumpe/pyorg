import os
from pathlib import Path
import json
from tempfile import TemporaryDirectory

from emacs import Emacs
from emacs.elisp import E
from .io import org_doc_from_json, agenda_item_from_json


class OrgDirectory:
	"""The directory where the user's org files are kept.

	path : pathlib.Path
		Absolute path to org directory.
	"""

	def __new__(cls, path):
		# Return argument when called with existing instance.
		if isinstance(path, OrgDirectory):
			return path
		return object.__new__(cls)

	def __init__(self, path):
		if path is self:
			return
		self.path = Path(path).expanduser().absolute()

	def __repr__(self):
		return '%s(%r)' % (type(self).__name__, str(self.path))

	def get_abs_path(self, path):
		"""Get absolute path from path relative to org directory.

		Path will be normalized with ".." components removed.

		Returns
		-------
		pathlib.Path

		Raises
		------
		ValueError
			If the path is not relative or is outside of the org directory
			(can happen if it contains ".." components).
		"""
		if os.path.isabs(path):
			raise ValueError('Paths should be relative to org directory.')

		path = self.path / os.path.normpath(path)

		if '..' in path.parts:
			raise ValueError('Path must be contained within org directory')

		return path

	def list_files(self, path=None, recursive=False, hidden=False):
		"""List org files within the org directory.

		Paths are relative to the org directory.

		Parameters
		----------
		path : str or pathlib.Path
			Optional subdirectory to search through.
		recursive : bool
			Recurse through subdirectories.
		hidden : bool
			Include hidden files.

		Returns
		-------
			Iterator over :class:`pathlib.Path` instances.
		"""
		abspath = self.path if path is None else self.get_abs_path(path)
		pattern = '**/*.org' if recursive else '*.org'

		for file in abspath.glob(pattern):
			if hidden or not file.name.startswith('.'):
				yield file.relative_to(self.path)

	def _get_org_file(self, path):
		"""Convert path to absolute, ensuring it is an org file within the directory.

		Parameters
		----------
		path : str or pathlib.Path

		Returns
		-------
		pathlib.Path

		Raises
		------
		ValueError
			If path is not within org directory or does not have .org extension.
		OSError
			If path is not a file.
		"""
		path = self.get_abs_path(path)

		if not path.is_file():
			raise OSError('%s is not a file' % path)
		if path.suffix != '.org':
			raise ValueError('Must be an org file')

		return path


class Org:
	"""Interface to org mode.

	Attributes
	----------
	emacs : pyorg.emacs.Emacs
	orgdir : .OrgDirectory
		Directory org files are read from.
	"""

	def __init__(self, emacs=None, orgdir=None):
		"""
		Parameters
		----------
		emacs : pyorg.emacs.Emacs
		orgdir : pathlib.Path
			Absolute path to org directory.
		"""
		self.emacs = emacs or Emacs()
		self._setup_emacs()

		if orgdir is None:
			orgdir = self.emacs.getresult('org-directory')

		self.orgdir = OrgDirectory(orgdir)

	def _setup_emacs(self):
		"""Perform initial setup with Emacs."""
		self.emacs.eval(E.require(E.Q('ox-json')))

	def _export_file(self, file, dest):
		el = E.with_current_buffer(
			E.find_file_noselect(str(file)),
			E.org_export_to_file(E.Q('json'), str(dest))
		)
		self.emacs.eval(el)

	def _read_file_direct(self, file):
		"""Read in JSON data for org file directly from Emacs."""
		file = Path(file)
		with TemporaryDirectory() as tmpdir:
			tmpfile = os.path.join(tmpdir, file.stem + '.json')
			self._export_file(file, tmpfile)
			with open(tmpfile) as f:
				return json.load(f)

	def read_org_file_direct(self, path, raw=False):
		"""Read and parse an org file directly from Emacs.

		Always reads the current file and does not use cached data, or perform
		any additional processing other than parsing.

		Parameters
		----------
		path : str or pathlib.Path
			File path relative to org directory.
		raw : bool
			Don't parse and just return raw JSON exported from Emacs.

		Returns
		-------
		pyorg.ast.OrgDocument or dict

		Raises
		------
		FileNotFoundError
		"""
		path = self.orgdir._get_org_file(path)
		data = self._read_file_direct(path)

		return data if raw else org_doc_from_json(data)

	def read_org_file(self, path):
		"""Read and parse an org file.

		Parameters
		----------
		path : str or pathlib.Path
			File path relative to org directory.

		Returns
		-------
		pyorg.ast.OrgDocument

		Raises
		------
		FileNotFoundError
		"""
		node = self.read_org_file_direct(path)

		return node

	def open_org_file(self, path, focus=False):
		"""Open an org file in the org directory for editing in Emacs.

		Parameters
		----------
		path : str or pathlib.Path
			File path relative to org directory.
		focus : bool
			Switch window/input focus to opened buffer.
		"""
		path = self.orgdir._get_org_file(path)
		el = E.find_file(str(path))
		if focus:
			el = [el, E.x_focus_frame(None)]
		self.emacs.eval(el)

	def agenda(self, key='t', raw=False):
		"""TODO Read agenda information.

		Parameters
		----------
		key : str
			TODO

		Returns
		-------
		list[dict]
		"""

		el = E.org_json_with_agenda_buffer(
			key,
			E.org_json_encode_agenda_buffer()
		)
		result = self.emacs.getresult(el, encode=False)
		data = json.loads(result)
		if raw:
			return data
		return list(map(agenda_item_from_json, data))
