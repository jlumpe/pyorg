.. py:currentmodule:: pyorg.ast


Org file structure
==================

The contents of an org file are represented internally in Org mode as an
Abstract Syntax Tree (AST). The nodes of this tree are org elements and objects,
such as headings, paragraphs, blocks, and text formatting/markup constructs.
See Org mode's
`documentation on the Element API <https://orgmode.org/worg/dev/org-element-api.html>`_
for more detailed information.


The document
------------

The :class:`OrgDocument` class stores data and metadata for an entire Org
document. The :attr:`OrgDocument.root` attribute stores the root of the
document's AST (see `Outline structure`_).


AST nodes
---------

Nodes are all represented as instances of :class:`OrgNode` or one of its
subclasses. They have several key attributes:

type
	The node's type, such as ``paragraph`` or ``list-item`` (see below).

ref
	A unique string ID assigned by Org mode during the export process. Can be used
	to look up targets of internal links.

properties
	A dictionary of named properties that depends on the node's type. See Org
	mode's documentation on the
	`Element API <https://orgmode.org/worg/dev/org-element-api.html>`_ for a
	list of all properties by type. Some additional properties are also added
	by ``ox-json`` on export.

contents
	Ordered list of this node's AST children and text contents. Elements of the
	list are either :class:`OrgNode` instances or strings.

keywords
	TODO


Node types
..........

The :attr:`OrgNode.type` attribute is an instance of :class:`OrgNodeType`. This
is a ``namedtuple`` which stores the type's name as well as its properties as
determined by the name's membership in the ``org-element-all-elements``,
``org-element-all-objects``, ``org-element-greater-elements``,
``org-element-object-containers``, and ``org-element-recursive-objects``
variables in Emacs.

:data:`pyorg.ast.ORG_NODE_TYPES` is a dictionary containing all node types
defined by Org mode, keyed by name.


Specialized ``OrgNode`` subclasses
..................................

Outline structure
+++++++++++++++++

An org document is structured as an outline tree, which is made of nested
headline elements. In Org mode, the root of the parse tree (and therefore the
outline tree) is a special element with type ``org-data``. All other outline
nodes correspond to ``headline`` elements. In pyorg these are represented with
the specialized classes :class:`OrgDataNode` and :class:`OrgHeadlineNode`, both
of which inherit from the abstract base class :class:`OrgOutlineNode`.

The contents of an outline node always consist of an optional ``section``
element followed by zero or more ``headline`` elements. For convenience these are
also stored in the :attr:`OrgOutlineNode.section` and
:attr:`OrgOutlineNode.subheadings` attributes.

You can use the :attr:`OrgOutlineNode.dump_outline` method to print a simple
representation of an outline node's subtree::

    >>> mydocument.root.dump_outline()

    Root
    0. Header for section one
     0. Header for subsection 1.1
       0. Header 1.1.1
     1. Header 1.2
    1. These are the header's title text
    2. Section three...



Timestamps
++++++++++

See :class:`OrgTimestampNode`


Tables
++++++

See :class:`OrgTableNode`

