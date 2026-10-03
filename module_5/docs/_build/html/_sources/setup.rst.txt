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

The project uses PostgreSQL for data storage and analysis.

Two related database configuration methods are used.

Direct Psycopg scripts such as ``load_data.py`` use the standard
PostgreSQL environment variables:

``PGHOST``
    PostgreSQL host name.

``PGPORT``
    PostgreSQL port.

``PGDATABASE``
    PostgreSQL database name.

``PGUSER``
    PostgreSQL user name.

``PGPASSWORD``
    PostgreSQL password.

The Flask and SQLAlchemy components use the ``DATABASE_URL``
environment variable.

A PostgreSQL SQLAlchemy connection string has the following form:

.. code-block:: text

   postgresql+psycopg://USERNAME:PASSWORD@localhost:5432/DATABASE_NAME

For example, in Windows PowerShell:

.. code-block:: powershell

   $password = Read-Host "PostgreSQL password" -AsSecureString
   $plainPassword = [System.Net.NetworkCredential]::new("", $password).Password
   $encodedPassword = [System.Uri]::EscapeDataString($plainPassword)

   $env:PGHOST = "localhost"
   $env:PGPORT = "5432"
   $env:PGDATABASE = "gradcafe"
   $env:PGUSER = "postgres"
   $env:PGPASSWORD = $plainPassword

   $env:DATABASE_URL = "postgresql+psycopg://postgres:$encodedPassword@localhost:5432/gradcafe"

The ``PG*`` variables are used by direct Psycopg scripts such as
``load_data.py``. ``DATABASE_URL`` is used when creating the SQLAlchemy
engine for the Flask and ORM components.

If the password contains characters that have special meaning in a URL,
it should be URL encoded before being placed in ``DATABASE_URL``.

Do not store the real PostgreSQL password in source code or commit it to
GitHub.

Tests can override database and application dependencies so that the
production PostgreSQL configuration is not required for every test.


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

The required marker groups can also be run together:

.. code-block:: console

   python -m pytest ./module_4/tests -m "web or buttons or analysis or db or integration"

The available markers are ``web``, ``buttons``, ``analysis``, ``db``,
and ``integration``.


Building the Sphinx Documentation
---------------------------------

From the repository root, build the HTML documentation with:

.. code-block:: console

   python -m sphinx -W -b html ./module_4/docs ./module_4/docs/_build/html

The ``-W`` option treats Sphinx warnings as errors so documentation
problems are detected during the build.

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
