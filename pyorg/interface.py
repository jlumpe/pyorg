import os
from glob import iglob
from pathlib import Path
import json

from .emacs import EmacsInterface, E
from .ast import org_node_from_json, parse_tags, assign_outline_ids







class OrgDirectory:
	"""The directory where the user's org files are kept.

	path : pathlib.Path
		Absolute path to org directory.
	"""

	def __init__(self, path):
		self.path = Path(path).expanduser().absolute()

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


class OrgInterface:
	"""Interface to org mode.

	Attributes
	----------
	emacs : pyorg.emacs.EmacsInterface
	orgdir : .OrgDirectory
		Directory org files are read from.
	export_dir : pathlib.Path
		Directory org file data is exported to.
	"""

	def __init__(self, emacs=None, orgdir=None, export_dir=None):
		"""
		Parameters
		----------
		emacs : pyorg.emacs.EmacsInterface
		orgdir : pathlib.Path
			Absolute path to org directory.
		export_dir : pathlib.Path
			Directory org file data is exported to.
		"""
		self.emacs = emacs or EmacsInterface()

		if orgdir is None:
			orgdir = self.emacs.getresult('org-directory')

		self.orgdir = OrgDirectory(orgdir)

	def _read_file_direct(self, file):
		"""Read in JSON data for org file directly from Emacs."""
		el = E.with_current_buffer(
			E.find_file_noselect(str(file)),
			E.org_json_encode_node(E.org_element_parse_buffer())
		)
		result = self.emacs.getresult(el, encode=False)
		return json.loads(result)

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
		pyorg.ast.OrgNode or dict

		Raises
		------
		FileNotFoundError
		"""
		path = self.orgdir.get_abs_path(path)

		if not path.is_file():
			raise FileNotFoundError(str(path))

		data = self._read_file_direct(path)

		return data if raw else org_node_from_json(data)

	def read_org_file(self, path, assign_ids=True):
		"""Read and parse an org file.

		Parameters
		----------
		path : str or pathlib.Path
			File path relative to org directory.
		assign_ids : bool
			Assign IDs to outline nodes. See :func:`pyorg.ast.assign_outline_ids`.

		Returns
		-------
		pyorg.ast.OrgNode

		Raises
		------
		FileNotFoundError
		"""
		node = self.read_org_file_direct(path)

		if assign_ids:
			assign_outline_ids(node)

		return node

	def edit_file(self, path):
		"""Open a file in the org directory for editing in Emacs.

		Parameters
		----------
		path : str or pathlib.Path
			File path relative to org directory.
		"""
		raise NotImplementedError()

	def agenda(self, key='t'):
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
		items = json.loads(result)

		for item in items:
			item['node'] = org_node_from_json(item['node'])
			item['tags'] = parse_tags(item['tags'] or '')

		return items
