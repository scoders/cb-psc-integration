.. _running_the_sandbox:

Running the Sandbox
===================

The easiest way to run the sandbox is with `docker` and `docker-compose`.

From within the repository root:

.. code-block:: bash

    docker-compose up

This will run redis, PostgreSQL, and the sandbox in separate containers.

To rebuild the container after making changes to the sandbox:

.. code-block:: base

    docker-compose build


Configuration API
-----------------

This page documents the steps required to install and run the
binary analysis sandbox, as well as its configuration API.

.. autoclass:: cb.psc.integration.config.Config
    :members:
