;;; pyorg.el --- Elisp code for the pyorg Python package  -*- lexical-binding: t; -*-

;; Copyright (C) 2019  Jared

;; Author: Jared <mjlumpe@gmail.com>
;; Version: 0.2.0
;; Keywords: outlines
;; Homepage: https://github.com/jlumpe/pyorg

;; Package-Requires: ((emacs "25") (org "9") (ox-json "0.2"))

;; This program is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation, either version 3 of the License, or
;; (at your option) any later version.

;; This program is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with this program.  If not, see <https://www.gnu.org/licenses/>.

;;; Commentary:

;; 

;;; Code:

(require 'ox)
(require 'ox-json)


(defun pyorg-export-org-file (file dest)
  "Export .org file FILE to JSON file DEST."
  (with-current-buffer (find-file-noselect file)
    (org-export-to-file 'json dest)))


(defun pyorg-open-org-file (path &optional focus)
  "Open an org file for interactive editing/viewing.

PATH is the path to the file to open.
If FOCUS is non-nil the window will be given active focus.

This function should switch to an existing buffer visiting the file if it
exists, rather than opening a new one."
  (find-file path)
  (if focus (x-focus-frame nil)))


(provide 'pyorg)
;;; pyorg.el ends here
