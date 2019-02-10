import os
from pathlib import Path

from flask import render_template, Markup, send_file, abort, url_for, redirect

from .app import app, emacs


@app.route('/')
def home():
	return render_template('home.html.j2')


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


def view_org_file(path):
	path = Path(path)
	htmlfile = app.config["ORG_PUBLISH_DIR"] / path.parent / (path.stem + '.html')

	if not htmlfile.is_file():
		return render_template('orgfile-404.html.j2', file=str(path)), 404

	with htmlfile.open() as fh:
		content = Markup(fh.read())

	return render_template(
		'orgfile.html.j2',
		file_content=content,
		file_name=path.name,
		file_title=path.stem,
		parents=path.parent.parts,
	)


def view_org_directory(path):
	path = Path(path)
	fullpath = app.config["ORG_PUBLISH_DIR"] / path

	dirs = []
	files = []

	for item in fullpath.iterdir():
		if item.is_dir():
			dirs.append(item.name)

		if item.is_file() and item.name.endswith('.html'):
			files.append(item.stem + '.org')

	*parents, dirname = ['root', *path.parts]

	print(repr(parents))
	print(repr(dirname))

	return render_template(
		'dirindex.html.j2',
		dirname=dirname,
		dirs=dirs,
		files=files,
		parents=parents,
	)


def get_other_file(filepath):
	fullpath = Path(app.config["ORG_PUBLISH_DIR"]) / filepath

	if not fullpath.exists():
		abort(404)

	if fullpath.is_dir():
		return redirect(url_for('viewfile', path=filepath + '/'))

	return send_file(str(fullpath))
