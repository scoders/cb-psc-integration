.. _rest_api:

REST API
========

This page documents the REST API exposed by the binary analysis sandbox,
which can be used to submit binaries for analysis, retrieve the current
results/result states, and delete any undesired results.

Submitting binaries
-------------------

Binaries can be submitted en-masse to the sandbox via a ``POST`` to the ``/analyze`` endpoint.

The ``/analyze`` endpoint takes a JSON payload with the following schema:

.. code-block::

    {
        "hashes": [<string>],
        "query": <string>,
        "limit": <int>?,
    }

Where:

* ``hashes`` is an array of SHA256 hashes for binaries stored on the UBS
* ``query`` is a Cb ThreatHunter process query, whose results will be retrieved from the UBS
* ``limit`` is the maximum number of items to take from ``query``'s results
  * If ``limit`` is not provided, all results are taken

Only *one* of ``hashes`` or ``query`` may be provided. ``limit`` only applies to ``query``.

Example:

.. code-block:: bash

    curl -XPOST http://localhost:5000/analyze --data '{ "hashes": ["6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b"] }'


On failure (schema mismatch), ``/analyze`` returns an HTTP 400.
In all other cases, ``/analyze`` returns ``{"success": true}``.

Scheduling queries
------------------

In addition to submitting binaries directly or via a one-shot query, the sandbox can be directed
to schedule a query for repeated retrieval via a ``POST`` to the ``/job`` endpoint.

The ``/job`` endpoint takes a JSON payload with the following schema:

.. code-block::

    {
        "query": <string>,
        "schedule": <string>,
        "repeat": "forever" | <int>,
        "limit": <int>?
    }

Where:

* ``query`` is a Cb ThreatHunter process query, whose results will be retrieved from the UBS
* ``schedule`` is a ``crontab(5)`` formatted schedule string
* ``repeat`` is the number of times to repeat the query on ``schedule``, or ``"forever"``
* ``limit`` is the maximum number of items to take from ``query``'s results
  * If ``limit`` is not provided, all results are taken

Example:

The following submits a query to be run every minute exactly twice:

.. code-block:: bash

    curl -XPOST http://localhost:5000/job --data \
      '{ "query": "process_name:cmd.exe", "schedule": "1 * * * *", "repeat": 2, "limit": 10 }'

On success, ``/job`` will return a payload with the following schema:

.. code-block::

    {
        "success": "true",
        "job_id": <string>,
    }


Where:

* ``job_id`` is a unique identifier for the underlying job

Removing a scheduled query
--------------------------

Scheduled queries added via a ``POST`` to ``/job`` can be removed via a ``DELETE`` to the
same endpoint with the following schema:

.. code-block::

    {
        "job_id": <string>
    }

Where:

* ``job_id`` is the unique job identifier previously returned by scheduled query creation

On failure (schema mismatch), ``/analyze`` returns an HTTP 400.
In all other cases, ``/analyze`` returns ``{"success": true}``.

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
        "kind": "kind",
        "items": []
    }

Where ``kind`` is one of ``hashes``, ``connector_names``, ``analysis_names``, or ``job_ids``
and ``items`` is a list of strings that should be matched against each ``kind`` for each
result.

Future iterations of this endpoint will also allow connector names, analysis names, and
job IDs as alternative deletion filters.

``/analyze`` **always** returns ``{"success": true}``. Future iterations will return
more information about the deleted analyses.

Retrieving hashes
-----------------

The list of all binary hashes analyzed (or currently being analyzed) by the sandbox can
be retrieved via a ``GET`` to ``/hashes``. No arguments or body is required.


Example::

.. code-block:: bash

    curl -XGET http://localhost:5000/hashes

Yields::

.. code-block:: json

    [
      "6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b",
    ]
