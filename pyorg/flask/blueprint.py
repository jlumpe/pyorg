from pathlib import Path
import json

from flask import (
	Blueprint, render_template, Markup, send_file, abort, url_for, redirect,
	current_app,
)
import jinja2

from .base import orginterface


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
	abspath = orginterface.get_abs_path(path)

	if not abspath.is_file():
		return render_template('orgfile-404.html.j2', file=str(path)), 404

	content = orginterface.read_org_file(path, assign_ids=True)

	from pyorg.html import OrgHtmlConverter
	converter = OrgHtmlConverter()

	html = Markup(converter.convert(content))

	return render_template(
		'orgfile.html.j2',
		ast=content,
		file_content=html,
		file_name=path.name,
		file_title=content.title or abspath.stem,
		parents=path.parent.parts,
		# source_json=json.dumps(data, indent=4, sort_keys=True),
		toc=make_toc(content),
	)


def view_org_directory(path):
	path = Path(path)
	abspath = orginterface.get_abs_path(path)

	dirs = []
	files = []

	for item in abspath.iterdir():
		if item.name.startswith('.'):
			continue

		if item.is_dir():
			dirs.append(item.name)

		if item.is_file() and item.name.endswith('.org'):
			files.append(item.name)

	*parents, dirname = ['root', *path.parts]

	return render_template(
		'dirindex.html.j2',
		dirname=dirname,
		dirs=dirs,
		files=files,
		parents=parents,
	)


def get_other_file(filepath):
	abspath = orginterface.get_abs_path(filepath)

	if not abspath.exists():
		abort(404)

	if abspath.is_dir():
		return redirect(url_for('viewfile', path=filepath + '/'))

	return send_file(str(abspath))


@pyorg_flask.route('/agenda')
def agenda():

	items = orginterface.agenda()

	from pyorg.html import OrgHtmlConverter
	converter = OrgHtmlConverter()

	for item in items:
		item['text_html'] = converter.make_headline_text(item['node'])

	items.sort(key=lambda item: (-item['priority'], item['file-relative'], *item['path']))

	return render_template(
		'agenda.html.j2',
		items=items,
		converter=converter,
	)
