"""(Partially) parse org files."""

import re


def read_file_keywords(file):
	"""Read file-level keywords from an .org file (without using Emacs).

	Limitations: only reads up to the first element in the initial section
	(excluding comments). If the initial section does contain such an element,
	any keywords directly preceding it (not separated with a blank line) will be
	considered affiliated keywords of that element and ignored.

	Will not parse org markup in keyword values.

	All keys are converted to uppercase.

	Keys which appear more than once will have values in a list.

	Parameters
	----------
	file
		String or open file object or stream in text mode.

	Returns
	-------
	dict
	"""
	if isinstance(file, str):
		file = file.splitlines()

	# The keywords we're sure of
	keywords = {}

	# Current set of keywords on consecutive lines. These might be affiliated
	# keywords for the following element instead of file-level keywords so we
	# can't be sure until we get to the next non-keyword line.
	current = {}

	# Merge current into keywords and clear it.
	def usecurrent():
		for key, values in current.items():
			keywords.setdefault(key, []).extend(values)
		current.clear()

	for line in file:
		line = line.rstrip('\n')

		# Match keyword
		match = re.fullmatch(r'#\+(\w+):(\s+.*)?', line)
		if match:
			key, value = match.groups()
			key = key.upper()
			value = (value or '').strip()
			current.setdefault(key, []).append(value)
			continue

		# Empty line
		if re.fullmatch(r'\s*', line):
			usecurrent()
			continue

		# Comment
		if re.match(r'\s*#', line):
			usecurrent()
			continue

		# Headline
		if re.match(r'\*+\s', line):
			break

		# Otherwise, it's some element. Don't use keywords directly preceding it
		# because they may be affiliated keywords not belonging to the file.
		current.clear()
		break

	usecurrent()

	return {key: values[0] if len(values) == 1 else values for key, values in keywords.items()}


def parse_tags(string):
	"""Parse tags from string.

	Parameters
	----------
	string : str
		Tags separated by colons.

	Returns
	-------
	list[str]
		List of tags.
	"""
	string = string.strip(':')
	if not string:
		return []
	return string.split(':')
