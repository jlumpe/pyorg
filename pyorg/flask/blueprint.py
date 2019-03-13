from pathlib import Path
import json

from flask import (
	Blueprint, render_template, Markup, send_file, abort, url_for, redirect,
	current_app,
)


pyorg_flask = Blueprint('pyorg', __name__, template_folder='templates')



@pyorg_flask.context_processor
def context_processor():
	return dict(
		favorite_files=current_app.config.get('ORG_FAVORITE_FILES', []),
	)


@pyorg_flask.route('/files/')
@pyorg_flask.route('/files/<path:path>')
def viewfile(path=''):
	if not path or path.endswith('/'):
		return view_org_directory(path)

	if path.endswith('.org'):
		return view_org_file(path)

	return get_other_file(path)


def view_org_file(path):
	path = Path(path)
	orgfile = current_app.config["ORG_DIR"] / path

	if not orgfile.is_file():
		return render_template('orgfile-404.html.j2', file=str(path)), 404

	from pyorg.elisp import E
	from .app import emacs
	el = E.with_current_buffer(
		E.find_file_noselect(str(orgfile.absolute())),
		E.org_json_encode_node(E.org_element_parse_buffer())
	)
	result = emacs.getresult(el, encode=False)

	from pyorg.ast import org_node_from_json
	data = json.loads(result)
	content = org_node_from_json(data)

	from pyorg.html import OrgHtmlConverter
	converter = OrgHtmlConverter()

	html = Markup(converter.convert(content).toprettyxml())

	return render_template(
		'orgfile.html.j2',
		file_content=html,
		file_name=path.name,
		file_title=path.stem,
		parents=path.parent.parts,
		source_json=json.dumps(data, indent=4, sort_keys=True),
	)


def view_org_directory(path):
	path = Path(path)
	fullpath = current_app.config["ORG_DIR"] / path

	dirs = []
	files = []

	for item in fullpath.iterdir():
		if item.name.startswith('.'):
			continue

		if item.is_dir():
			dirs.append(item.name)

		if item.is_file() and item.name.endswith('.org'):
			files.append(item.name)

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
	fullpath = Path(current_app.config["ORG_DIR"]) / filepath

	if not fullpath.exists():
		abort(404)

	if fullpath.is_dir():
		return redirect(url_for('viewfile', path=filepath + '/'))

	return send_file(str(fullpath))


@pyorg_flask.route('/agenda')
def agenda():

	from pyorg.elisp import E
	from .app import emacs
	el = E.org_json_with_agenda_buffer('t',
		E.org_json_encode_agenda_buffer()
	)
	result = emacs.getresult(el, encode=False)
	data = json.loads(result)

	data.sort(key=lambda item: (item['file-relative'], *item['path']))

	return render_template(
		'agenda.html.j2',
		items=data,
	)
