Quick start
===========


Getting the data from Emacs to Python
-------------------------------------

Create the following example file in Emacs:

.. include:: example.org
   :literal:


Use the ``ox-json-export-to-json`` command to export it as ``example.json``.
Now, read the JSON file with pyorg:

.. code-block:: python

   import json
   from pyorg.io import org_doc_from_json

   with open('example.json') as f:
      data = json.load(f)

   doc = org_doc_from_json(data)


Explore the AST structure
-------------------------

``doc`` is an :class:`~pyorg.ast.OrgDocument` which contains all data read from
the file. Its ``root`` attribute the root node of the AST:

>>> doc.root
OrgDataNode(type='org-data')


Its has the type ``org-data``, which is always the root node of the buffer.
Its contents are a ``section`` node and some more ``headline`` nodes:


>>> doc.root.contents
[OrgNode(type='section'),
 OrgOutlineNode(type='headline'),
 OrgOutlineNode(type='headline'),
 OrgOutlineNode(type='headline')]


We can print a simple representation of the outline tree with the
:meth:`~pyorg.ast.OrgOutlineNode.dump_outline` method:


>>> doc.root.dump_outline()
Root
  0. Header 1
    0. Header 2
      0. Header 3
        0. Header 4
  1. Markup
  2. A headline with a TODO and tags


Get the 2nd headline (3rd item in root node's contents) and print the full
AST subtree, along with each node's properties:


>>> hl2 = doc.root[2]
>>> hl2.dump(properties=True)
headline
  :archivedp       = False
  :commentedp      = False
  :footnote-section-p = False
  :level           = 1
  :post-affiliated = 120
  :post-blank      = 2
  :pre-blank       = 0
  :priority        = None
  :raw-value       = 'Markup'
  :tags            = []
  :title           = ['Markup']
  :todo-keyword    = None
  :todo-type       = None
  0 section
    :post-affiliated = 129
    :post-blank      = 2
    0 paragraph
      :post-affiliated = 129
      :post-blank      = 0
      0 'A paragraph with '
      1 bold
        :post-blank      = 0
        0 'bold'
      2 ', '
      3 italic
        :post-blank      = 0
        0 'italic'
      4 ', '
      5 underline
        :post-blank      = 0
        0 'underline'
      6 ', '
      7 strike-through
        :post-blank      = 0
        0 'strike'
      8 ', '
      9 verbatim
        :post-blank      = 0
        :value           = 'verbatim'
      10 ', and '
      11 code
        :post-blank      = 0
        :value           = 'code'
      12 '\nobjects.\n'


Check third headline's properties to get the TODO information and tags:


>>> hl3 = doc.root[3]
>>> hl3.properties
{'title': ['A headline with a TODO and tags'],
 'deadline': OrgTimestampNode(type='timestamp'),
 'post-affiliated': 301,
 'commentedp': False,
 'archivedp': False,
 'footnote-section-p': False,
 'post-blank': 0,
 'todo-type': 'todo',
 'todo-keyword': 'TODO',
 'tags': ['tag1', 'tag2'],
 'priority': 65,
 'level': 1,
 'pre-blank': 0,
 'raw-value': 'A headline with a TODO and tags'}
