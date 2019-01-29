"""Interface with Emacs and run commands."""

from subprocess import run, PIPE


class EmacsInterface:
	"""Interface to Emacs program.

	Parameters
	----------
	cmd : list[str]
		Base command to run Emacs.
	"""

	def __init__(self, cmd):
		self.cmd = list(cmd)

	def run(self, args, check=True):
		"""Run the Emacs command with a list of arguments.

		Parameters
		----------
		args : list[str]
			List of strings.
		check : bool
			Check the return code is zero.

		Returns
		-------
		subprocess.CompletedProcess

		Raises
		------
		subprocess.CalledProcessError
			If ``check=True`` and return code is nonzero.
		"""
		return run([*self.cmd, *args], check=check, stdout=PIPE, stderr=PIPE)

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
		return self.run(args, **kwargs).stdout.decode()

	def eval(self, source, **kwargs):
		"""Evaluate ELisp source code and return output.

		Parameters
		----------
		source : str
			Elisp code.
		kwargs
			Passed to :meth:`getoutput`.

		Returns
		-------
		str
			Value of stdout.
		"""
		return self.getoutput(['-eval', source], **kwargs)
