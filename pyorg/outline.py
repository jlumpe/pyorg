"""Tools for working with an org file's outline structure, especially its headlines."""


def headline_identifiers(headline, file=None):
	"""Get information from a headline that can be used to locate it in an org file.

	Parameters
	----------
	headline : pyorg.ast.OrgHeadlineNode
	file : str
		Path to the file the headline resides in.

	Returns
	-------
	dict
		Dictionary that may contain the following keys:
		* ``'file'`` - Value of the ``file`` argument, if not None.
		* ``'id'`` - The headline's ``ID`` property.
		* ``'custom_id'`` - The headline's ``CUSTOM_ID`` property.
		* ``'text'`` - The headline's ``raw-value`` property (raw org markup,
		  not including the TODO keyword and tags).
		* ``'position'`` - The headline's position in the buffer (value of the
		  ``begin`` property.
	"""
	ids = {}

	if file is not None:
		ids['file'] = str(file)
	if headline.keywords.get('ID') is not None:
		ids['id'] = headline.keywords['ID']
	if headline.keywords.get('CUSTOM_ID') is not None:
		ids['custom_id'] = headline.keywords['CUSTOM_ID']
	if headline.properties.get('raw-value') is not None:
		ids['text'] = headline['raw-value']
	if headline.properties.get('begin') is not None:
		ids['position'] = headline['begin']

	return ids
