from flask import Flask

from pyorg.emacs import EmacsInterface


app = Flask(__package__)


app.config.update(
	ORG_DIR='/Users/student/org/',
	ORG_PUBLISH_DIR='/Users/student/tmp/pyorg-publish',
)


emacs = EmacsInterface(['emacsclient'], client=True)
