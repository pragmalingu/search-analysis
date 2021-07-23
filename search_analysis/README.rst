Search_Analysis
===============

|PyPI| |Status| |Python Version| |License|

|Read the Docs| |Tests| |Codecov|

|pre-commit| |Black|

.. |PyPI| image:: https://img.shields.io/pypi/v/search_analysis.svg
   :target: https://pypi.org/project/search_analysis/
   :alt: PyPI
.. |Status| image:: https://img.shields.io/pypi/status/search_analysis.svg
   :target: https://pypi.org/project/search_analysis/
   :alt: Status
.. |Python Version| image:: https://img.shields.io/pypi/pyversions/search_analysis
   :target: https://pypi.org/project/search_analysis
   :alt: Python Version
.. |License| image:: https://img.shields.io/pypi/l/search_analysis
   :target: https://opensource.org/licenses/MIT
   :alt: License
.. |Read the Docs| image:: https://img.shields.io/readthedocs/search_analysis/latest.svg?label=Read%20the%20Docs
   :target: https://search_analysis.readthedocs.io/
   :alt: Read the documentation at https://search_analysis.readthedocs.io/
.. |Tests| image:: https://github.com/pragmalingu/search_analysis/workflows/Tests/badge.svg
   :target: https://github.com/pragmalingu/search-analysis/actions?workflow=Tests
   :alt: Tests
.. |Codecov| image:: https://codecov.io/gh/pragmalingu/search_analysis/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/pragmalingu/search-analysis
   :alt: Codecov
.. |pre-commit| image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit
.. |Black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
   :alt: Black


Features
--------


**Use-Case: Analyze Single Approach**

* Get Metrics: Precision, Recall, F-Score
* Find queries that perform especially bad/good
* Analyze false positives, false negatives and true positives
* For every query get score, field value, highlighting

**Use-Case Compare Two Approaches**

* Visualization of metrics side by side
* Find queries with biggest difference
* Analyze false positives, false negatives, true positives and calculate disjoint sets
* Get scores visualized side by side

(For now it's only possible to work with Elasticsearch)



Requirements
------------

* TODO


Installation
------------

.. highlight:: shell

============
Installation
============

To build the documents you have to run the nox task responsible for building thte documents

    nox --session=docs

Stable release
--------------

To install Search Analysis, run this command in your terminal:

.. code-block:: console

    $ pip install search_analysis

This is the preferred method to install Search Analysis, as it will always install the most recent stable release.

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.

.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/


From sources
------------

The sources for Search Analysis can be downloaded from the `Github repo`_.

You can either clone the public repository:

.. code-block:: console

    $ git clone git://github.com/pragmalingu/search-analysis

Or download the `tarball`_:

.. code-block:: console

    $ curl -OJL https://github.com/pragmalingu/search-analysis/tarball/main

Once you have a copy of the source, you can install it with:

.. code-block:: console

    $ python setup.py install


.. _Github repo: https://github.com/pragmalingu/search-analysis
.. _tarball: https://github.com/pragmalingu/search-analysis/tarball/main



Usage
-----


Contributing
------------

Contributions are very welcome.
To learn more, see the `Contributor Guide`_.


License
-------

Distributed under the terms of the `MIT license`_,
*Search_Analysis* is free and open source software.


Issues
------

If you encounter any problems,
please `file an issue`_ along with a detailed description.


Help
------------

For questions you can contact us via E-Mail or through our website (https://www.pragmalingu.de/).


Credits
-------

This project was generated from `@cjolowicz`_'s `Hypermodern Python Cookiecutter`_ template.

.. _@cjolowicz: https://github.com/cjolowicz
.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _MIT license: https://opensource.org/licenses/MIT
.. _PyPI: https://pypi.org/
.. _Hypermodern Python Cookiecutter: https://github.com/cjolowicz/cookiecutter-hypermodern-python
.. _file an issue: https://github.com/pragmalingu/search_analysis/issues
.. _pip: https://pip.pypa.io/
.. github-only
.. _Contributor Guide: CONTRIBUTING.rst
.. _Usage: https://search_analysis.readthedocs.io/en/latest/usage.html
