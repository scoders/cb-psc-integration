# Taxii Connector

Connector for pulling and converting STIX information from TAXII Service Providers into CB Feeds.

## Introduction

This document describes how to configure the CB ThreatHunter TAXII connector.
This connector allows for the importing of STIX data by querying one or more TAXII services and retrieving that data and then converting it into CB feeds using the CB JSON format for IOCs. 

## Layout
The connector code is located at `connectors/taxii` directory in the `cb-psc-integration` repo.
It is a major refactor of the original Taxii connector for CB Response, but care has been taken to preserve the logic as well as variable and function names. 
Its functionality is decomposed in to following files:

1. `connector.py`:
Contains the logic to connect to Taxii servers via the `cabby` library.
The `TaxiiConnector` class extends the sandbox's base `Connector` interface, using objects of `TaxiiSiteConnector` class to talk to each individual Taxii servers.
The entypoint function--`analyze()` inside `TaxiConnector`--is triggered every time an `analyze` POST request is made the sandbox's REST frontend.

2. `config.yml`:
Enables per-Taxii-server-level configuration options.
Almost the same config options as support by the original CB Response Taxii connector, except for being in a yaml format.
Example:
```
    eclecticiq:
        site: test.taxiistand.com
        discovery_path: /read-only/services/discovery
        collection_management_path: /read-only/services/collection-management
        poll_path: /read-only/services/poll
        use_https: True
        ssl_verify: False
        cert_file:
        key_file:
        default_score: 5
        username:
        password:
        collections: '*'
        start_date: 2019-09-20 00:00:00
        minutes_to_advance: 1440
        ca_cert:
        http_proxy_url:
        https_proxy_url:
        reports_limit: 10000
        fail_limit: 100
```
The only new option is `fail_limit` which provides a knob to control the number of attempts per-collection before giving up trying to get (empty/malformed) STIX data out of a Taxii server.
This is similar to the hardcoded `10` limit for `num_times_empty_content_blocks` in the original connector. 

Note:
The number of reports to batch before being disptached as feed to the CB TH backend (`feed_size`), as well as the connector's analysis timeout limit (`binary_timeout`) are connector-independent config options residing in `cb-psc-connector/config.yml`. 
The Taxii connector respects this batching of results by `yield`ing reports to the sandbox as and when ready.

3. `stix_parse.py`:
Contains the logic to parse STIX observables from the XML data returned by the Taxii server.
Basically an extension of the original connector's `cybox_parse.py`.
As in the original, the following IOC types are extracted from STIX data:

* MD5 Hashes
* Domain Names
* IP-Addresses
* IP-Address Ranges


4. `feed_helper.py`:
Logic to advance the `begin_date` and `end_date` fields while polling the Taxii server to iteratively get per-collection STIX content.
This is tied to the `start_date` and `minutes_to_advance` config options as above.
Extracted from the original connector's `cb_feed_util.py`.


## Issues
1. The `taxiistand` Taxii server yields empty contents for some reason; however `hailataxii` provides useful IOC-rich content.
2. There is a `URL` IOC-type that is not currently being extracted.
3. Reports seem to get lost at CbTh backend. Querying for reports via cbapi's `list-iocs` lists fewer IOCs/reports than what gets successfully shipped to the CB TH feed. 
4. At par with its Response counterpart, the ThreatHunter Taxii connector only pulls STIX content from a Taxii server, and does not perform ingestion of the input `binary` (in the entrypoint `analyze()` function) to the server. The `binary` is essentially ignored.
5. Every time the sandbox calls the Taxii connector (which might be on every `analyze` REST POST request), the plugin would start repeating content fetching from the server, disregarding content pulled on the previous run. The logic to pull/send only new content needs to be incorporated in the connector.

