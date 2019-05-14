.. _rest_api:

REST API
========

This page documents the REST API exposed by the binary analysis sandbox,
which can be used to submit binaries for analysis, retrieve the current
results/result states, and delete any undesired results.

Submitting binaries
-------------------

Binaries can be submitted en-masse to the sandbox via a ``POST`` to the ``/analyze`` endpoint.

The ``/analyze`` endpoint takes a JSON payload that looks like this:

.. code-block:: json

    {
        "hashes": []
    }

Where each member of ``hashes`` is a SHA256 hash for a binary stored on the UBS.

Example:

.. code-block:: bash

    curl -XPOST http://localhost:5000/analyze --data '{ "hashes": ["6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b"] }'


``/analyze`` **always** returns ``{"success": true}``.

Retrieving results
------------------

Analysis results can be retrieved by issuing a ``GET`` to the ``/analysis`` endpoint.

Like ``/analyze``, ``/analysis`` takes a JSON payload that looks like this:

.. code-block:: json

    {
        "hashes": []
    }

Where ``hashes`` is the list of binary hashes to retrieve results for.

Example:

.. code-block:: bash

    curl -XGET http://localhost:5000/analysis --data '{ "hashes": ["6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b"] }'

Which yields something like this:

.. code-block:: json

    {
      "data": {
        "completed": {
          "6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b": [
            {
              "analysis_name": "null",
              "connector_name": "null",
              "error": false,
              "id": 3,
              "job_id": "d104e6e6-4cf4-45b7-9ec7-75cbdc771413",
              "payload": {},
              "scan_time": "Thu, 18 Apr 2019 19:50:35 GMT",
              "score": 100,
              "sha256": "6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b"
            },
            {
              "analysis_name": "dummy:dummy",
              "connector_name": "yara",
              "error": false,
              "id": 2,
              "job_id": "22c2d601-5fb9-41f5-9506-3d84410a39b5",
              "payload": [],
              "scan_time": "Thu, 18 Apr 2019 19:50:20 GMT",
              "score": 10,
              "sha256": "6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b"
            },
            {
              "analysis_name": "microsoft:microsoft",
              "connector_name": "yara",
              "error": false,
              "id": 1,
              "job_id": "22c2d601-5fb9-41f5-9506-3d84410a39b5",
              "payload": [
                {
                  "data": "TQBpAGMAcgBvAHMAbwBmAHQA",
                  "identifier": "$microsoft",
                  "offset": 21050
                }
              ],
              "scan_time": "Thu, 18 Apr 2019 19:50:20 GMT",
              "score": 50,
              "sha256": "6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b"
            }
          ]
        },
        "pending": []
      },
      "success": true
    }

Observe that the members of each binary under the ``completed`` object reflect the members
documented for :py:class:`AnalysisResult` objects.

The ``pending`` list contains the ``job_id`` of any analyses hadn't completed
as of the request.

Deleting results
----------------

Analysis results can be deleted by issuing a ``DELETE`` to ``/analysis``.

Like the other endpoints, this has a JSON payload:

.. code-block:: json

    {
        "hashes": []
    }

Where ``hashes`` is the list of binary hashes whose results should be removed.

Future iterations of this endpoint will also allow connector names, analysis names, and
job IDs as alternative deletion filters.

``/analyze`` **always** returns ``{"success": true}``. Future iterations will return
more information about the deleted analyses.
