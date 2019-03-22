from pathlib import Path
import json

from flask import (
	Blueprint, render_template, Markup, send_file, abort, url_for, redirect,
	current_app,
)
import jinja2


pyorg_flask = Blueprint('pyorg', __name__, template_folder='templates')



@pyorg_flask.context_processor
def context_processor():
	return dict(
		favorite_files=current_app.config.get('ORG_FAVORITE_FILES', []),
	)

@jinja2.contextfilter
@pyorg_flask.app_template_test('orgnode')
def test_orgast(value):
	from pyorg.ast import OrgNode
	return isinstance(value, OrgNode)


@pyorg_flask.route('/files/')
@pyorg_flask.route('/files/<path:path>')
def viewfile(path=''):
	if not path or path.endswith('/'):
		return view_org_directory(path)

	if path.endswith('.org'):
		return view_org_file(path)

	return get_other_file(path)


def _make_toc(node):
	return (node.title, node.id, list(map(_make_toc, node.outline_children)))

def make_toc(root):
	return list(map(_make_toc, root.outline_children))

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

	from pyorg.ast import org_node_from_json, assign_outline_ids
	data = json.loads(result)
	content = org_node_from_json(data)
	assign_outline_ids(content)

	from pyorg.html import OrgHtmlConverter
	converter = OrgHtmlConverter()

	html = Markup(converter.convert(content).toprettyxml())

	return render_template(
		'orgfile.html.j2',
		ast=content,
		file_content=html,
		file_name=path.name,
		file_title=content.title or path.stem,
		parents=path.parent.parts,
		source_json=json.dumps(data, indent=4, sort_keys=True),
		toc=make_toc(content),
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
