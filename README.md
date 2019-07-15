# pyorg
[![Documentation Status](https://readthedocs.org/projects/pyorg/badge/?version=latest)](https://pyorg.readthedocs.io/en/latest/?badge=latest)

Python library for working with Emacs org mode.


Check out the [Quick start](https://pyorg.readthedocs.io/en/latest/quick-start.html) section in the documentation.


## Quick demo

Communicate with running Emacs server and execute elisp code:

```python3
>>> from pyorg import Emacs
>>> emacs = Emacs.client()
>>> emacs.getresult('(+ 1 2)')
3
```

High-level interface to Org mode:

```python3
>>> from pyorg import Org
>>> org = Org(emacs)
>>> org.orgdir  # Obtained automatically from org-directory variable in Emacs
OrgDir('/home/jlumpe/org/')

>>> org.orgdir.list_files(recursive=True)
[PosixPath('tasks.org'),
 PosixPath('inbox.org'),
 PosixPath('presentations.org'),
 PosixPath('misc.org'),
 PosixPath('research/ideas.org'),
 PosixPath('research/lab-notebook.org'),
 PosixPath('research/meetings.org'),
 PosixPath('projects/pyorg.org'),
 PosixPath('topics/control-theory.org'),
 PosixPath('topics/optogenetics.org'),
 PosixPath('topics/modeling.org'),
 PosixPath('topics/productivity.org'),
 PosixPath('topics/math.org')]
```

Read in an org file:

```python3
>>> doc = org.read_org_file('topics/math.org')
>>> doc.keywords
{'title': ['Math'],
 'file_tags': None,
 'author': ['jlumpe'],
 'creator': 'Emacs 26.2 (Org mode 9.2.4)',
 'date': [],
 'description': [],
 'email': 'jlumpe@*****.edu',
 'language': 'en',
 'export_errors': []}
```

View file's outline structure:

```python3
doc.root.dump_outline()
Root
  0. Linear algebra
    0. Distance between covariance matrices
    1. Dual vector space
    2. Tensors
    3. Gramian Matrix
  1. Calculus
    0. Resources
    1. Chain rule for Hessian Matrices
    2. Log-transforming function inputs and outputs
    3. Parameter Jacobians of function roots
    4. Local sensitivity of initial value problems
  2. Probability theory
    0. Probability theory terms
    1. Probability distributions
    2. Statistical difference
    3. Fisher information
    4. Stochastic processes
    5. Misc
    6. Information geometry
    7. Resources
  3. Differential Geometry
  4. Stochastic Calculus
    0. Stochastic differential equations
  5. Misc
    0. Log scale plots of log ratios
```

View data structure of a subsection:

```python3
>>> header = doc.root[1][3]
>>> header
OrgHeadlineNode(type='headline')

>>> header.dump(properties=True)
headline
  :archivedp       = False
  :commentedp      = False
  :footnote-section-p = False
  :level           = 2
  :post-affiliated = 2
  :priority        = None
  :raw-value       = '[[wikipedia:Gramian_Matrix][Gramian Matrix]]'
  :tags            = []
  :title           = [OrgNode(type='link')]
  :todo-keyword    = None
  :todo-type       = None
  0 section
    0 quote-block
      0 paragraph
        0 'In linear algebra, the Gram matrix (Gramian matrix or Gramian) of a set of vectors '
        1 latex-fragment
          :value           = '$v_1, \\ldots, v_n$'
        2 '\nin an inner product space is the Hermitian matrix of inner products, whose entries are given by\n'
        3 latex-fragment
          :value           = '$G_{ij} = \\langle v_1, v_2 \\rangle$'
        4 '\n'
      1 paragraph
        0 'An important application is to compute linear independence: a set of vectors are linearly\nindependent if and only if the Gram determinant (the determinant of the Gram matrix) is non-zero.\n'
      2 paragraph
        0 '-- Wikipedia\n

...
```

Convert to HTML:

```python3
>>> from pyorg.convert.html import to_html
>>> print(to_html(header))
```

```html
<div class="org-header-container org-header-level-2" id="org9e9d94c">
	<h3 class="org-node org-headline"><span class="org-header-text"><a class="org-linktype-https org-node org-link" href="https://en.wikipedia.org/wiki/Gramian_Matrix">Gramian Matrix</a></span></h3>
	<section class="org-node org-section">
		<blockquote class="org-node org-quote-block">
			<p class="org-node org-paragraph">In linear algebra, the Gram matrix (Gramian matrix or Gramian) of a set of vectors \(v_1, \ldots, v_n\)
in an inner product space is the Hermitian matrix of inner products, whose entries are given by
\(G_{ij} = \langle v_1, v_2 \rangle\)
</p>
			<p class="org-node org-paragraph">An important application is to compute linear independence: a set of vectors are linearly
independent if and only if the Gram determinant (the determinant of the Gram matrix) is non-zero.
</p>
			<p class="org-node org-paragraph">-- Wikipedia
</p>
		</blockquote>
	</section>
	<div class="org-header-container org-header-level-3" id="orgbe766cb">
		<h4 class="org-node org-headline"><span class="org-header-text">Examples</span></h4>
		<section class="org-node org-section">
			<p class="org-node org-paragraph">In finite dimensions, for \(V = \begin{bmatrix} v_1 &amp; \ldots &amp; v_n \end{bmatrix}\), \(G\) is just \(V^T V\).
</p>
		</section>
	</div>
	<div class="org-header-container org-header-level-3" id="orgad99b82">
		<h4 class="org-node org-headline"><span class="org-header-text">Properties</span></h4>
		<section class="org-node org-section">
			<ul class="org-node org-plain-list">
				<li class="org-node org-item">
					<p class="org-node org-paragraph">Positive-semidefinite
</p>
				</li>
				<li class="org-node org-item">
					<p class="org-node org-paragraph">Determinant is zero iff. vectors are linearly independent.
</p>
				</li>
			</ul>
		</section>
	</div>
</div>
```
