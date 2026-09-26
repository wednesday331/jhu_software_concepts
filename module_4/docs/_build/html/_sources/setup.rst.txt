Setup and Usage
===============

Project Requirements
--------------------

GradCafe Analytics requires Python 3.11 or later and PostgreSQL.

The Module 4 dependencies are listed in:

.. code-block:: text

   module_4/requirements.txt

From the repository root, dependencies can be installed with:

.. code-block:: console

   python -m pip install -r module_4/requirements.txt


PostgreSQL Configuration
------------------------

The application uses PostgreSQL through SQLAlchemy.

The database connection is configured using the ``DATABASE_URL``
environment variable.

A PostgreSQL SQLAlchemy connection string has the following form:

.. code-block:: text

   postgresql+psycopg://USERNAME:PASSWORD@localhost:5432/DATABASE_NAME

For example, in Windows PowerShell:

.. code-block:: powershell

   $env:DATABASE_URL = "postgresql+psycopg://postgres:PASSWORD@localhost:5432/gradcafe"

If the password contains special URL characters, it should be URL encoded
before being placed in the connection string.

The application reads ``DATABASE_URL`` when creating the SQLAlchemy
engine. Tests may override the database configuration so that production
database settings are not required for every test.


Running the Flask Application
-----------------------------

From the repository root, move into the Module 4 source directory:

.. code-block:: console

   cd module_4/src

Then start the Flask application:

.. code-block:: console

   python app.py

The application starts the Flask development server and provides the
GradCafe analysis webpage.


Running the Test Suite
----------------------

Return to the repository root and run:

.. code-block:: console

   python -m pytest ./module_4/tests -v

The Module 4 ``pytest.ini`` file automatically enables coverage
measurement and requires 100 percent source-code coverage.

Individual test groups can also be selected using Pytest markers.

For example:

.. code-block:: console

   python -m pytest ./module_4/tests -m "web or buttons or analysis or db or integration"

Other available markers include ``buttons``, ``analysis``, ``db``, and
``integration``.


Building the Sphinx Documentation
---------------------------------

From the repository root, build the HTML documentation with:

.. code-block:: console

   python -m sphinx -b html ./module_4/docs ./module_4/docs/_build/html

After a successful build, the documentation homepage is located at:

.. code-block:: text

   module_4/docs/_build/html/index.html

On Windows, it can be opened with:

.. code-block:: powershell

   Start-Process .\module_4\docs\_build\html\index.html


Continuous Integration
----------------------

GitHub Actions runs the Module 4 test suite automatically when changes
are pushed to the repository.

The workflow is located at:

.. code-block:: text

   .github/workflows/tests.yml

The workflow starts PostgreSQL, configures the database environment,
installs the required CI dependencies, and runs the full Pytest suite
with coverage.