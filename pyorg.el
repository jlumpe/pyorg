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
(require 'org-element)
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


(cl-defun pyorg-transcode-headline-ql (headline info &rest options)
  "Encode a single headline from org-ql.

HEADLINE is the parsed headline to encode.
INFO is the plist of org-export-json options."
  (let* ((buffer (current-buffer))
         (parent-index (org-element-property :parent-index headline))
         (extra-properties (plist-get options :extra-properties)))
    (setq extra-properties
      (append extra-properties
        (ox-json-make-alist info
          `(
            (file string ,(buffer-file-name buffer))
            (path (array string) ,(org-get-outline-path t))
            (tags-all (array string) ,(org-get-tags))))))
    (plist-put options :extra-properties extra-properties)
    (apply #'ox-json-export-node-base headline info options)))

(defun pyorg--ql-export-hl (info)
  "Callback for `org-ql-select' to collect JSON values of headlines.

INFO is the plist of ox-json export options.

(This actually isn't meant to be used as the callback directly, because it
requires an argument. The actual callback should call this function with the
info plist within a closure)."
  (pyorg-transcode-headline-ql
    (org-element-headline-parser (line-end-position))
    info))

(defun pyorg--ql-collect-tree-file (info)
  (let* ((files-table (plist-get info :ql-files-hash))
         (buffer (current-buffer))
         (file (buffer-file-name buffer))
         (existing (gethash file files-table)))
    (or existing
      (let* ((headlines (plist-get info :ql-headlines))
             (next-index (length headlines))
             (file-env (org-export-get-environment))
             (properties
               (ox-json-document-properties
                 (org-combine-plists info file-env))))
        (push
          (cons 'file (ox-json-encode-string file))
          properties)
        (puthash file next-index files-table)
        (push
          (ox-json-make-object "org-node" info
            `(
                (type string "org-data")
                (contents array nil)
                (properties nil ,(ox-json-encode-alist-raw nil properties info))
                (ref string nil)))
          headlines)
        (plist-put info :ql-headlines headlines)
        next-index))))

(defun pyorg--ql-collect-tree-parent (info)
  (save-mark-and-excursion
    (org-up-heading-all 1)
    (pyorg--ql-collect-tree info)))

(defun pyorg--ql-collect-tree (info)
  "Parse headline at current point and add to list of not already present. Return its index."
  (let* ((hl-table (plist-get info :ql-headline-hash))
         (buffer (current-buffer))
         (file (buffer-file-name buffer))
         (key (list file (point)))
         (existing (gethash key hl-table)))
    (or existing
      ; Not already in hash map, export and add
      (let* ((headline (org-element-headline-parser (line-end-position)))
             (level (org-element-property :level headline))
             (parent-index
               (if (equal level 1)
                 (pyorg--ql-collect-tree-file info)
                 (pyorg--ql-collect-tree-parent info))))
        (plist-put (ox-json-node-properties headline) :parent-index parent-index)
        ; Add to hash table and headlines list
        (let* ((headlines (plist-get info :ql-headlines))
               (next-index (length headlines))
               (hl-encoded
                 (pyorg-transcode-headline-ql headline info
                   :extra-properties
                   (ox-json-make-alist info
                     `(
                       (parent-index number ,parent-index))))))
          (puthash key next-index hl-table)
          (push hl-encoded headlines)
          (plist-put info :ql-headlines headlines)
          next-index)))))

(cl-defun pyorg--init-ql (info &key include-parents)
  (plist-put info :ql-headlines nil)
  (plist-put info :ql-headline-hash (make-hash-table :test 'equal))
  (plist-put info :ql-files-hash (make-hash-table :test 'equal)))

(cl-defun pyorg-ql-select-tree (files query &optional ext-plist &key info)
  (unless info
    (setq info (ox-json--init-backend ext-plist))
    (pyorg--init-ql info))
  (let* ((action (lambda () (pyorg--ql-collect-tree info)))
         (results (org-ql-select files query :action action))
         (headlines (plist-get info :ql-headlines)))
    (ox-json-encode-alist-raw
      "ql-results"
      (list
        (cons 'results (ox-json-encode-array results info 'number))
        (cons 'headlines (ox-json-encode-array-raw (nreverse headlines) info)))
      info)))

(defun pyorg-ql-select (files query &optional ext-plist info)
  "Query headlines using `org-ql-select' and return results as JSON.

FILES and QUERY are the first two arguments to `org-ql-select' and are the list
of files to search and the query form, respectively.
EXT-PLIST is a property list with external parameters overriding default settings.
INFO is an existing plist of export options."
  (unless info
    (setq info (ox-json--init-backend ext-plist)))
  (ox-json-encode-array-raw
    (org-ql-select files query
      :action (lambda () (pyorg--ql-export-hl info)))
    info))


(provide 'pyorg)
;;; pyorg.el ends here
