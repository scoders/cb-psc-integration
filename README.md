cb-psc-integration
------------------

Integration code for building Predictive Security Cloud connectors.

This repository contains two components: the binary analysis sandbox and the connector API.

## Usage

### Dependencies

You'll need `redis-server` and everything inside `setup.py`.

### Running the binary analysis sandbox

The binary analysis sandbox has two components: the workers/binary cache and a REST frontend.

You can start everything with:

```bash
make serve
```

### Submitting binaries

You can submit one or more binaries for analysis with a `POST` to `/analyze`:

```bash
curl -XPOST http://localhost:5000/analyze --data '{ "hashes": ["6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b"] }'
```

To retrieve the current analysis results for one or more binaries, send a `GET` to `/analysis`:

```bash
curl -XGET http://localhost:5000/analysis --data '{ "hashes": ["6f88fb88ffb0f1d5465c2826e5b4f523598b1b8378377c8378ffebc171bad18b"] }'
```

Which will yield something like this:

```json
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
            },
            {
              "data": "TQBpAGMAcgBvAHMAbwBmAHQA",
              "identifier": "$microsoft",
              "offset": 94200
            },
            {
              "data": "TWljcm9zb2Z0",
              "identifier": "$microsoft",
              "offset": 152740
            },
            {
              "data": "TWljcm9zb2Z0",
              "identifier": "$microsoft",
              "offset": 323522
            },
            {
              "data": "bWljcm9zb2Z0",
              "identifier": "$microsoft",
              "offset": 323578
            },
            {
              "data": "TWljcm9zb2Z0",
              "identifier": "$microsoft",
              "offset": 323711
            },
            {
              "data": "bWljcm9zb2Z0",
              "identifier": "$microsoft",
              "offset": 323854
            },
            {
              "data": "bWljcm9zb2Z0",
              "identifier": "$microsoft",
              "offset": 324144
            },
            {
              "data": "bWljcm9zb2Z0",
              "identifier": "$microsoft",
              "offset": 324232
            },
            {
              "data": "TQBpAGMAcgBvAHMAbwBmAHQA",
              "identifier": "$microsoft",
              "offset": 355542
            },
            {
              "data": "TQBpAGMAcgBvAHMAbwBmAHQA",
              "identifier": "$microsoft",
              "offset": 355870
            },
            {
              "data": "TQBpAGMAcgBvAHMAbwBmAHQA",
              "identifier": "$microsoft",
              "offset": 356046
            },
            {
              "data": "VwBpAG4AZABvAHcAcwA=",
              "identifier": "$windows",
              "offset": 21070
            },
            {
              "data": "VwBJAE4ARABPAFcAUwA=",
              "identifier": "$windows",
              "offset": 152792
            },
            {
              "data": "V2luZG93cw==",
              "identifier": "$windows",
              "offset": 320831
            },
            {
              "data": "V2luZG93cw==",
              "identifier": "$windows",
              "offset": 323721
            },
            {
              "data": "V2luZG93cw==",
              "identifier": "$windows",
              "offset": 323781
            },
            {
              "data": "d2luZG93cw==",
              "identifier": "$windows",
              "offset": 324173
            },
            {
              "data": "V2luZG93cw==",
              "identifier": "$windows",
              "offset": 324255
            },
            {
              "data": "d2luZG93cw==",
              "identifier": "$windows",
              "offset": 324295
            },
            {
              "data": "VwBpAG4AZABvAHcAcwA=",
              "identifier": "$windows",
              "offset": 355626
            },
            {
              "data": "VwBpAG4AZABvAHcAcwA=",
              "identifier": "$windows",
              "offset": 356068
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
```

## Writing connectors

All connectors are subclasses of `cb.psc.integration.Connector`.

Here's a simple connector that does almost nothing:

```python
import time

from cb.psc.integration.connector import Connector


class NullConnector(Connector):
    name = "null"

    def analyze(self, binary, data):
        time.sleep(5)
        return self.result(binary, analysis_name=self.name, score=100)
```

All connectors **must** override the `analysis` method. See the docs for the meaning of the
`binary` and `data` parameters, as well as the `result` method.

See the YARA connector under [src/connectors/yara](./src/connectors/yara) for a more detailed
example.
