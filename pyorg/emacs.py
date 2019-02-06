"""Interface with Emacs and run commands."""

import sys
from subprocess import run, PIPE
import json
from ast import literal_eval


def make_progn(forms):
	return '(progn\n%s)' % '\n  '.join(forms)

def _print_json(source):
	return '(princ (json-encode %s))' % source


class EmacsInterface:
	"""Interface to Emacs program.

	Attributes
	----------
	cmd : list[str]
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

	def __init__(self, cmd, client=False, verbose=1):
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
		if not isinstance(source, str):
			source = make_progn(source)

		result = self.run(['-eval', source], **kwargs)

		if process:
			return result
		else:
			return self._getoutput(result)

	def getjson(self, source, wrap=True, **kwargs):
		"""Get parse JSON from the command's output.

		Parameters
		----------
		source : str or list
			Elisp code to evaluate.
		wrap : bool
			If True ``source`` (or its last element if a list) will be wrapped in
			a command to print its value to JSON. Set to False if `source` will
			already be printing JSON.

		Returns
		-------
		Parsed JSON value.
		"""
		if isinstance(source, str):
			source = [source]
		else:
			source = list(source)

		if wrap:
			source[-1] = _print_json(source[-1])

		source.insert(0, "(require 'json)")

		result = self.eval(source, **kwargs)
		if self.is_client:
			result = literal_eval(result)  # Why is this required?
		return json.loads(result)

