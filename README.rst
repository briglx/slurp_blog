**********************************
Slurp Blog
**********************************

This project will copy blog post images and text from blogger.

Use
==========

Blog slurp doesn't provide too many options. You can list them by running `python main.py -h`:

.. code-block:: python

    usage: main.py [-h] [--blog_url BLOG_URL] [--year YEAR]

    Slurp posts and images from blogger.

    optional arguments:
    -h, --help            show this help message and exit
    --blog_url BLOG_URL, -b BLOG_URL
                            Blog Url
    --year YEAR, -y YEAR  Year to slurp

For Time of use plans pass in the argument `is_tou`

.. code-block:: python

    from datetime import datetime, timedelta
    from srpenergy.client import SrpEnergyClient

    accountid = 'your account id'
    username = 'your username'
    password = 'your password'
    end_date = datetime.now()
    start_date = datetime.now() - timedelta(days=2)

    client = SrpEnergyClient(accountid, username, password)
    usage = client.usage(start_date, end_date, True)

    date, hour, isodate, kwh, cost = usage[0]

Development
===========

Style Guidelines
----------------

This project enforces quite strict `PEP8 <https://www.python.org/dev/peps/pep-0008/>`_ and `PEP257 (Docstring Conventions) <https://www.python.org/dev/peps/pep-0257/>`_ compliance on all code submitted.

We use `Black <https://github.com/psf/black>`_ for uncompromised code formatting.

Summary of the most relevant points:

 - Comments should be full sentences and end with a period.
 - `Imports <https://www.python.org/dev/peps/pep-0008/#imports>`_  should be ordered.
 - Constants and the content of lists and dictionaries should be in alphabetical order.
 - It is advisable to adjust IDE or editor settings to match those requirements.

Ordering of imports
-------------------

Instead of ordering the imports manually, use `isort <https://github.com/timothycrosley/isort>`_.

.. code-block:: bash

    pip3 install isort
    isort -rc .

Use new style string formatting
-------------------------------

Prefer `f-strings <https://docs.python.org/3/reference/lexical_analysis.html#f-strings>`_ over ``%`` or ``str.format``.

.. code-block:: python

    #New
    f"{some_value} {some_other_value}"
    # Old, wrong
    "{} {}".format("New", "style")
    "%s %s" % ("Old", "style")

One exception is for logging which uses the percentage formatting. This is to avoid formatting the log message when it is suppressed.

.. code-block:: python

    _LOGGER.info("Can't connect to the webservice %s at %s", string1, string2)


Testing
-------

As it states in the `Style Guidelines`_ section all code is checked to verify the following:

 - All the unit tests pass
 - All code passes the checks from the linting tools

Local testing is done using `Tox <https://tox.readthedocs.io/en/latest/>`_. To start the tests, activate the virtual environment and simply run the command:

.. code-block:: bash

    tox

**Testing outside of Tox**

Running ``tox`` will invoke the full test suite. To be able to run the specific test suites without tox, you'll need to install the test dependencies into your Python environment:

.. code-block:: bash

    pip3 install -r requirements_test.txt

Now that you have all test dependencies installed, you can run tests on the project:

.. code-block:: bash

    isort -rc .
    codespell  main.py
    black main.py
    flake8 main.py
    pylint main.py
    pydocstyle main.py


References
==========

- https://docs.microsoft.com/en-us/azure/container-instances/container-instances-using-azure-container-registry


.. |screenshot-pipeline| image:: https://raw.github.com/briglx/AzureBillingReports/master/docs/BillingArchitectureOverview.png