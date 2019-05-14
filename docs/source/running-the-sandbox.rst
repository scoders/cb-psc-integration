.. _running_the_sandbox:

Running the Sandbox
===================

Installing the Sandbox
----------------------

The steps below document the sandbox's installation *for development or local testing purposes*.

Start by installing some dependencies: you'll need ``redis-server`` and Python 3.6 or later.

For systems with ``apt``:

.. code-block:: bash

    sudo apt install redis-server python3.6 python3-setuptools

Then, clone the cb-psc-integration repository:

.. code-block:: bash

    git clone https://github.com/carbonblack/cb-psc-integration
    cd cb-psc-integration

Then, create a virtualenv and install the sandbox's Python dependencies into it:

.. code-block:: bash

    python3 -m venv env
    source env/bin/activate
    python3 setup.py install

Optionally, modify ``config.yml``. Refer to the Configuration API below for valid options.

Finally, start everything with ``make``:

.. code-block:: bash

    make serve

The REST API should now be available on :py:attr:`Config.flask_host` at port :py:attr:`Config.flask_port`.

Configuration API
-----------------

This page documents the steps required to install and run the
binary analysis sandbox, as well as its configuration API.

.. autoclass:: cb.psc.integration.config.Config
    :members:
