Graph-Talk
==========

Graph-talk is a library for structured data processing to solve tasks like parsing,
interpreting, or converting in a simple and comprehensible manner.

The library uses 3 key concepts to achieve the goal: a graph-like representation of
information and its processing; a dialog-like communication between the model and
the process; and a handler-event approach to recognize the input messages.

.. contents:: Table of Contents


Features
========

* Easy to learn architecture
* Highly customizable
* Plain Python 2.7.5 or higher
* Very small footprint

Check the docs_ for the documentation and examples_ folder for examples of
lexing, interpreting, and converting using Graph-talk.

Installation
============

From pypi_::

    $ pip install graph-talk

Easy_install::

    $ easy_install graph-talk

Clone from github_::

    $ git clone git://github.com/krvss/graph-talk.git

Setuptools::

    $ cd graph-talk
    $ sudo python setup.py install

Testing::

    $ python setup.py test

Documentation with sphinx_::

    $ sphinx-build -b html docs docs/html

Support
=======
If you're having problems using the project, make the issue_ at GitHub.

Copyrights and License
======================

``graph-talk`` is protected by Apache Software License. Check the LICENSE_ file for
details.

.. _LICENSE: https://github.com/krvss/graph-talk/blob/master/LICENSE
.. _docs: https://pythonhosted.org/graph-talk/
.. _examples: https://github.com/krvss/graph-talk/tree/master/examples
.. _github: https://github.com
.. _pypi: http://pypi.python.org/pypi/graph-talk
.. _issue: https://github.com/krvss/graph-talk/issues
.. _sphinx: http://sphinx-doc.org/
