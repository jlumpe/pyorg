"""Setuptools installation script for pyorg package."""

from setuptools import setup, find_packages
import re


# Get contents of README file
with open('README.md') as fh:
	readme_contents = fh.read()


# Read version from root module __init__.py
with open('pyorg/__init__.py') as fh:
	init_contents = fh.read()
	version_match = re.search('^__version__ = ["\']([^"\']+)["\']', init_contents, re.M)

	if not version_match:
		raise RuntimeError('Unable to get version string')

	version = version_match.group(1)


requirements = [
]

setup_requirements = ['pytest-runner']

test_requirements = ['pytest']


setup(
	name='pyorg',
	version=version,
	description='Package for working with Emacs org-mode files',
	long_description=readme_contents,
	author='Jared Lumpe',
	author_email='mjlumpe@gmail.com',
	url='https://github.com/jlumpe/pyorg',
	python_requires='>=3.5',
	install_requires=requirements,
	setup_requires=setup_requirements,
	tests_require=test_requirements,
	packages=find_packages(),
	include_package_data=True,
	# license='',
	# classifiers='',
	# keywords=[],
	# platforms=[],
	# provides=[],
	# requires=[],
	# obsoletes=[],
)
