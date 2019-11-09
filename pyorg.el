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

(eval-when-compile (require 'cl-lib))

(require 'cl-lib)
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


(defconst pyorg-link-escape-chars '(91 93 37)
  "Characters to escape (URL encode) when locating a headline by
its text content using `org-link-search'.")

(defun pyorg--goto-headline-by-id (id current-buffer)
  "Move to the headline with the given ID property.

If CURRENT-BUFFER is non-nil will restrict to headlines in the currently
active buffer.

Return non-nil if the headline was found."
  ; TODO
  (org-id-goto id)
  t)

(defun pyorg--goto-headline-by-custom-id (custom-id)
  "Move to the headline in the current buffer with the given CUSTOM-ID property.

Return non-nil if the headline was found."
  (let ((org-link-search-must-match-exact-headline t)
        (org-link-search-inhibit-query t))
    (ignore-errors
      (org-link-search (concat "#" custom-id)))))

(defun pyorg--goto-headline-by-text (text)
  "Move to the (first?) headline in the current buffer with the given text content.

TEXT is more or less the value of the raw-value property of the headline element.

Return non-nil if the headline was found."
  (let ((org-link-search-must-match-exact-headline t)
        (org-link-search-inhibit-query t)
        (escaped (org-link-escape text pyorg-link-escape-chars)))
    (ignore-errors
      (org-link-search (concat "*" escaped)))))

(defun pyorg--goto-headline-by-position (pos)
  "Move to the headline in the current buffer at position POS.

Return non-nil if there actually was a headline at the given position, otherwise
return nil and don't actually change the marker position."
  ; TODO actually check for a headline
  (goto-char pos))

(cl-defun pyorg-goto-headline (file &key id custom-id position text focus)
  "Switch to a file's buffer and move to a specific headline within it.

FILE is the path to the headline's file (required unless ID is given).
ID is the headline's ID property.
CUSTOM-ID is the headline's CUSTOM_ID property.
POSITION is the headline's position in the file.
TEXT is the headline's exact text (excluding TODO keyword and tags, along with
the whitespace adjacent to them).
If FOCUS is non-nil the frame containing the buffer's window will be given
active focus by the window system.

The function attempts to find the headline using the following arguments in
order, stopping when one is successful: ID, CUSTOM-ID, POSITION, and TEXT.
At least one of these arguments must be specified. FILE is optional if ID
is given, the latter three require FILE be given to work.

Returns non-nil if target headline was found."
  (if (not (or id custom-id position text))
    (error "At least one of ID, CUSTOM-ID, POSITION, or TEXT must be specified."))
  (if file
    ; With file
    (progn
      (pyorg-switch-to-file-buffer file focus)
      ; Stop at the first successful one
      (or
        (if id
          (pyorg--goto-headline-by-id id t))
        (if custom-id
          (pyorg--goto-headline-by-custom-id custom-id))
        (if position
          (pyorg--goto-headline-by-position position))
        (if text
          (pyorg--goto-headline-by-text text))))
    ; Without file
    (if id
      (pyorg--goto-headline-by-id id nil)
      (error "FILE must be non-nil unless ID is given."))))


(provide 'pyorg)
;;; pyorg.el ends here
