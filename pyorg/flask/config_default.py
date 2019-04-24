"""Default configuration file for pyorg flask app."""


# Root org directory (defaults to value of `org-directory` in Emacs)
# PYORG_ORG_DIRECTORY = '~/org'

# Base command to run Emacs in non-interactive mode
# PYORG_EMACS_CMD = ['emacs', '--batch']
PYORG_EMACS_CMD = ['emacsclient']

# Whether PYORG_EMACS_CMD is running emacsclient
PYORG_EMACS_IS_CLIENT = True

# List of favorite files (relative to org directory).
PYORG_FAVORITE_FILES = []
