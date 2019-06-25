"""Test pyorg.parse"""

from io import StringIO
from textwrap import dedent

from pyorg.parse import read_file_keywords


def test_read_file_keywords():
	"""Test the read_file_keywords() function."""

	file1 = dedent("""\
	#+TITLE: My file title

	# Whitespace before and after
	#+WHITESPACE:    \tit's trimmed     \t  

	#+EMPTY:

	#+lowercase: lowercase
	
	#+MULTI: value1

	# Another comment
	
	# Blank line with extra whitespace
	     \t\t  \t \t  

	#+multi: value2

	#+AFFILIATED: won't get read
	#+AFFILIATED2: This won't either
	This is a (paragraph) element

	#+AFTER_ELEM: also won't get read.

	* Headline
	""")

	file1_kw = read_file_keywords(file1)
	assert file1_kw == {
		'TITLE': 'My file title',
		'WHITESPACE': 'it\'s trimmed',
		'EMPTY': '',
		'LOWERCASE': 'lowercase',
		'MULTI': ['value1', 'value2'],
	}

	# Try from stream
	assert read_file_keywords(StringIO(file1)) == file1_kw

	# Edge cases where last keyword precedes EOF or first file

	file2 = dedent("""\
	#+TITLE: My file title
	
	#+BEFORE_EOF: foo\
	""")

	assert read_file_keywords(file2) == {
		'TITLE': 'My file title',
		'BEFORE_EOF': 'foo',
	}

	file3 = dedent("""\
	#+TITLE: My file title
	
	#+BEFORE_HEADLINE: foo
	* Headline
	""")

	assert read_file_keywords(file3) == {
		'TITLE': 'My file title',
		'BEFORE_HEADLINE': 'foo',
	}
