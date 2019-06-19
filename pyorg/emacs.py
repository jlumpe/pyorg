"""Interface with Emacs and run commands."""

import sys
import os
from subprocess import run, PIPE
import json
from ast import literal_eval
from tempfile import TemporaryDirectory

from .elisp import ElispAstNode, E, Raw


def _get_forms_seq(seq):
	forms = []
	for item in seq:
		if isinstance(item, str):
			forms.append(Raw(item))
		elif isinstance(item, ElispAstNode):
			forms.append(item)
		else:
			raise TypeError('Sequence elements must be strings or AST nodes')
	return forms


def get_form(src):
	"""Get Elisp form from string, AST node, or sequence of these."""
	if isinstance(src, ElispAstNode):
		return src

	if isinstance(src, str):
		return Raw(src)

	return E.progn(*_get_forms_seq(src))


def get_forms_list(src):
	"""Get source as list of forms from string, AST node, or sequence of these."""
	if isinstance(src, ElispAstNode):
		return [src]

	if isinstance(src, str):
		return [Raw(src)]

	return _get_forms_seq(src)


class Emacs:
	"""Interface to Emacs program.

	Attributes
	----------
	cmd : str or list[str]
		Base command to run Emacs.
	is_client : bool
	    Whether the command runs ``emacsclient``.
	verbose : int
		1 to echo stderr of Emacs command, 2 to echo stdout. 0 turns off.

	Parameters
	----------
	cmd : list[str]
		Base command to run Emacs.
	client : bool
	    Whether the command runs ``emacsclient``.
	verbose : int
		1 to echo stderr of Emacs command, 2 to echo stdout. 0 turns off.
	"""

	def __init__(self, cmd=('emacs', '--batch'), client=False, verbose=1):
		if isinstance(cmd, str):
			self.cmd = [cmd]
		else:
			self.cmd = list(cmd)

		self.is_client = client
		self.verbose = verbose

	def run(self, args, check=True, verbose=None):
		"""Run the Emacs command with a list of arguments.

		Parameters
		----------
		args : list[str]
			List of strings.
		check : bool
			Check the return code is zero.
		verbose : int or None
			Overrides :attr:`verbose` attribute if not None.

		Returns
		-------
		subprocess.CompletedProcess

		Raises
		------
		subprocess.CalledProcessError
			If ``check=True`` and return code is nonzero.
		"""
		if verbose is None:
			verbose = self.verbose

		result = run([*self.cmd, *args], check=False, stdout=PIPE, stderr=PIPE)

		if verbose >= 1 and result.stderr:
			print(result.stderr.decode(), file=sys.stderr)
		if verbose >= 2 and result.stdout:
			print(result.stdout.decode())

		if check:
			result.check_returncode()

		return result

	def _getoutput(self, result):
		"""Get the output of a command.

		Parameters
		----------
		result : subprocess.CompletedProcess

		Returns
		-------
		str
		"""
		return result.stdout.decode()

	def getoutput(self, args, **kwargs):
		"""Get output of command.

		Parameters
		----------
		args : list[str]
			List of strings.
		kwargs
			Passed to :meth:`run`.

		Returns
		-------
		str
			Value of stdout.
		"""
		return self._getoutput(self.run(args, **kwargs))

	def eval(self, source, process=False, **kwargs):
		"""Evaluate ELisp source code and return output.

		Parameters
		----------
		source : str or list
			Elisp code. If a list of strings will be enclosed in ``progn``.
		process : bool
			If True return the :class:`subprocess.CompletedProcess` object,
			otherwise just return the value of ``stdout``.
		kwargs
			Passed to :meth:`run`.

		Returns
		-------
		str or subprocess.CompletedProcess
			Command output or completed process object, depending on value of
			``process``.
		"""
		source = str(get_form(source))
		result = self.run(['-eval', source], **kwargs)

		if process:
			return result
		else:
			return self._getoutput(result)

	def _result_from_stdout(self, form, **kwargs):
		"""Get result by reading from stdout."""

	def _result_from_tmpfile(self, form, **kwargs):
		"""Get result by having Emacs write to tmp file and reading from Python."""
		with TemporaryDirectory() as tmpdir:
			fname = os.path.join(tmpdir, 'emacs-output')
			el = E.with_temp_file(fname, E.insert(form))
			self.eval(el)
			with open(fname) as fobj:
				return fobj.read()

	def getresult(self, source, is_json=False, **kwargs):
		"""Get parsed result from evaluating the Elisp code.

		Parameters
		----------
		source : str or list
			Elisp code to evaluate.
		is_json : bool
			True if the result of evaluating the code is already a string of
			JSON-encoded data.

		Returns
		-------
		Parsed value.
		"""
		form = get_form(source)

		if not is_json:
			form = E.progn(
				E.require(E.Q('json')),
				E.json_encode(form)
			)

		result = self._result_from_tmpfile(form, **kwargs)

		return json.loads(result)
