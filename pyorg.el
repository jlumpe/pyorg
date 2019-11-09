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


(defun pyorg-switch-to-file-buffer (file &optional focus)
  "Switch to a buffer visiting FILE and display it in a window.

FILE is the path to the file to open. If not absolute it is taken to be relative
to `org-directory'.
If FOCUS is non-nil set the window system's focus to the
active frame.

Uses an existing buffer visiting the file if possible, otherwise
creates one. If this buffer is already displayed in some window
select it, otherwise open it in a new window (where?). The window
(and its frame, if different than the current one) are then given
focus.

Returns the selected buffer."
  (setq file (expand-file-name file org-directory))
  (let ((buffer (find-file-noselect file)))
    (pop-to-buffer
      buffer
      '(display-buffer-reuse-window
        (inhibit-same-window . nil)
        (inhibit-switch-frame . nil)
        (reusable-frames . t)))
    (if focus (x-focus-frame nil))
    buffer))


(provide 'pyorg)
;;; pyorg.el ends here
