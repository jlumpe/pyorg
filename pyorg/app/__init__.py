import os

from flask import Flask, render_template, Markup, send_file, abort

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


@app.route('/org/<path:path>')
def viewfile(path):
	name = os.path.basename(path)
	ext = os.path.splitext(name)[1]
	fullpath = os.path.join(EXPORT_DIR, path)

	if ext == '.html':
		try:
			content = Markup(get_file_content(fullpath))
			return render_template('vieworg.html.j2', file_content=content, page_title=name)

		except FileNotFoundError:
			return render_template('vieworg-404.html.j2', file=fullpath), 404

	else:
		try:
			return send_file(fullpath)
		except FileNotFoundError:
			abort(404)
