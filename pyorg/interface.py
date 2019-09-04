from emacs.elisp import E
from .files import OrgDirectory, DirectFileLoader


class Org:
	"""Interface to org mode.

	Attributes
	----------
	emacs : pyorg.emacs.Emacs
	orgdir : pyorg.files.OrgDirectory
		Directory org files are read from.
	loader : pyorg.files.OrgFileLoader
		Loader used to read .org file data.
	"""

	def __init__(self, emacs, orgdir=None, loader=None):
		"""
		Parameters
		----------
		emacs : pyorg.emacs.Emacs
		orgdir : str or pathlib.Path or .OrgDirectory
			Absolute path to org directory. If None will use value of
			``org-directory`` variable in Emacs.
		loader : .OrgFileLoader
			Loader to use to read .org file data.
		"""
		self.emacs = emacs
		self._setup_emacs()

		if orgdir is None:
			orgdir = self.emacs.getresult('org-directory')

		self.orgdir = OrgDirectory(orgdir)

		self.direct_loader = DirectFileLoader(self.emacs, self.orgdir)
		self.loader = self.direct_loader if loader is None else loader

	def _setup_emacs(self):
		"""Perform initial setup with Emacs."""
		self.emacs.eval(E.require(E.Q('ox-json')))

	def read_org_file_direct(self, file, raw=False):
		"""Read and parse an org file directly from Emacs.

		Always reads the current file and does not use cached data, or perform
		any additional processing other than parsing.

		Parameters
		----------
		file : str or pathlib.Path
			Path to file to load (relative paths are interpreted relative to
			org directory).
		raw : bool
			Don't parse and just return raw JSON exported from Emacs.

		Returns
		-------
		pyorg.ast.OrgDocument or dict

		Raises
		------
		FileNotFoundError
		"""
		return self.direct_loader.load_file(file, raw=raw)

	def read_org_file(self, file, raw=None):
		"""Read and parse an org file.

		Parameters
		----------
		file : str or pathlib.Path
			Path to file to load (relative paths are interpreted relative to
			org directory).
		raw : bool
			Don't parse and just return raw JSON exported from Emacs.

		Returns
		-------
		pyorg.ast.OrgDocument

		Raises
		------
		FileNotFoundError
		"""
		return self.loader.load_file(file, raw=raw)

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
