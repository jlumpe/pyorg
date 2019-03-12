"""Basic Flask application."""

from flask import Flask, render_template

from pyorg.emacs import EmacsInterface
from .blueprint import pyorg_flask


app = Flask(__package__)


app.config.update(
	ORG_DIR='/Users/student/org/',
	ORG_FAVORITE_FILES=[
		'topics/math.org',
		'thesis/references.org',
	],
)


emacs = EmacsInterface(['emacsclient'], client=True)


@app.route('/')
def home():
	return render_template('home.html.j2')


app.register_blueprint(pyorg_flask)
