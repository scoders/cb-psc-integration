.. _connector_api:

PSC Connector API
=================

This page documents the public interfaces exposed by cb-psc-integration when
developing new connectors.

All connectors are singletons, and inherit from the `Connector` class.

The simplest possible connector just overrides the `analyze` method:

.. code-block:: python

    from cb.psc.integration.connector import Connector

    class NullConnector(Connector):
        name = "null"

        def analyze(self, binary, data):
            time.sleep(15)

            return self.result(binary, analysis_name=self.name, score=100)


.. autoclass:: cb.psc.integration.connector.Connector
    :members:

.. autoclass:: cb.psc.integration.connector.ConnectorConfig
    :members:

.. autoclass:: cb.psc.integration.database.IOC
    :members:

.. autoclass:: cb.psc.integration.database.IOC.MatchType
    :members:

.. autoclass:: cb.psc.integration.database.AnalysisResult
    :members:

.. autoclass:: cb.psc.integration.database.Binary
    :members:
