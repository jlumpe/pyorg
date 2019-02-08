import os

from flask import (Flask, render_template, Markup, send_file, abort, url_for,
                   redirect)

from pyorg.emacs import EmacsInterface


app = Flask(__name__)


emacs = EmacsInterface(['emacsclient'], client=True)


ORG_DIR = '/Users/student/org/'
EXPORT_DIR = '/Users/student/tmp/pyorg-publish'

def get_file_content(path):
	with open(path) as fh:
		return fh.read()


@app.route('/')
def home():
	return render_template('home.html.j2')


def view_org_file(filepath):
	dirname, filename = os.path.split(filepath)
	name = os.path.splitext(filename)[0]

	fullpath = os.path.join(EXPORT_DIR, filepath)
	htmlfile = os.path.join(EXPORT_DIR, dirname, name + '.html')

	try:
		content = Markup(get_file_content(htmlfile))

	except FileNotFoundError:
		return render_template('orgfile-404.html.j2', file=fullpath), 404

	return render_template(
		'orgfile.html.j2',
		file_content=content,
		page_title=filename,
		filename=filename,
		filetitle=name,
		parents=dirname.split(os.path.sep),
	)


def view_org_directory(dirpath):
	fullpath = os.path.join(EXPORT_DIR, dirpath)

	dirs = []
	files = []

	for entry in os.scandir(fullpath):
		if entry.is_dir():
			dirs.append(entry.name)

		if entry.is_file() and entry.name.endswith('.html'):
			files.append(entry.name.rsplit('.', 1)[0] + '.org')

	*parents, dirname = ['root', *dirpath.rstrip('/').split()]

	return render_template(
		'dirindex.html.j2',
		dirname=dirname,
		page_title=dirname,
		dirs=dirs,
		files=files,
		parents=parents,
	)


def get_other_file(filepath):
	fullpath = os.path.join(EXPORT_DIR, filepath)

	if not os.path.exists(fullpath):
		abort(404)

	if os.path.isdir(fullpath):
		return redirect(url_for('viewfile', path=filepath + '/'))

	return send_file(fullpath)


@app.route('/org/')
def orgroot():
	return view_org_directory('')


@app.route('/org/<path:path>')
def viewfile(path):
	if path.endswith('/'):
		return view_org_directory(path)

	if path.endswith('.org'):
		return view_org_file(path)

	return get_other_file(path)
