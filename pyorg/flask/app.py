"""Basic Flask application."""

from flask import Flask, render_template

from pyorg.emacs import EmacsInterface
from .blueprint import pyorg_flask


app = Flask(__package__)


app.config.from_object(__package__ + '.config_default')
app.config.from_envvar('PYORG_CONFIG', silent=True)


emacs = EmacsInterface(['emacsclient'], client=True)


@app.route('/')
def home():
	return render_template('home.html.j2')


app.register_blueprint(pyorg_flask)
