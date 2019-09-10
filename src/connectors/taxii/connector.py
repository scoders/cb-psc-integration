import logging
import traceback
import os
from functools import lru_cache
from pathlib import Path
from cabby import create_client

from cb.psc.integration.connector import Connector, ConnectorConfig

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class TaxiiConfig(ConnectorConfig):
    site: str = ''
    discovery_path: str = ''
    collection_management_path: str = ''
    poll_path: str = ''
    use_https: bool = False
    ssl_verify: bool = False
    cert_file: str = None
    key_file: str = None
    default_score: int = 50
    username: str = None
    password: str = None
    collections: str = '*'
    start_date: str = '2019-01-01 00:00:00'
    minutes_to_advance: int = 60
    ca_cert: str = None
    http_proxy_url: str = None
    https_proxy_url: str = None




class TaxiiConnector(Connector):
    Config = TaxiiConfig
    name = "taxii"

    # TODO: add try and except
    def create_taxii_client(self):
        conf = self.config
        
        client = create_client(conf.site,
                               use_https=conf.use_https,
                               discover_path=conf.discovery_path)
        
        client.set_auth(username=conf.username,
                        password=conf.password,
                        verify_ssl=conf.ssl_verify,
                        ca_cert=conf.ca_cert,
                        cert_file=conf.cert_file,
                        key_file=conf.key_file)

    
        proxy_dict = dict()
        if conf.http_proxy_url:
            proxy_dict['http'] = conf.http_proxy_url
        if conf.https_proxy_url:
            proxy_dict['https'] = conf.https_proxy_url
        if proxy_dict:
            client.set_proxies(proxy_dict)

        self.client = client


    def create_uri(self, config_path):
        uri = None
        if config_path and self.config.site:
            if self.config.use_https:
                uri = 'https://'
            else:
                uri = 'http://'
            uri = uri + self.config.site + config_path
        return uri        


    # TODO: add try and except
    def query_collections(self):
        uri = self.create_uri(self.config.collection_management_path)
        collections = self.client.get_collections(uri=uri) # autodetect if uri=None
        for collection in collections:
            logger.info(f"Collection Name: {collection.name}, Collection Type: {collection.type}")
        return collections

    
    def import_collection(self, collection):
        reports = []
        uri = self.create_uri(self.config.poll_path)

        while True:
            num_times_empty_content_blocks = 0
            try:
                #TODO: resume
            except Exception as e:
                logger.info(traceback.format_exc())
            
        data_set = False
        if collection.type == 'DATA_SET':
            data_set = True

        

    def import_collections(self, available_collections):
        desired_collections = self.config.collections
        desired_collections = [x.strip() for x in desired_collections.lower().split(',')]
        
        want_all = False
        if '*' in desired_collections:
            want_all = True

        for collection in available_collections:
            if collection.type != 'DATA_FEED' and collection.type != 'DATA_SET':
                continue
            if not collection.available:
                continue
            if want_all or collection.name.lower() in desired_collections:
                self.import_collection(collection)
        

    def analyze(self, binary, data):   # TODO:ignoring binary for now
        results = []
    
        self.create_taxii_client()  # TODO: make this part of init, not analyze
                                    # assuming analyze is called repeatedly

        available_collections = self.query_collections()
        if len(available_collections) == 0:
            logger.info('Unable to find any collections.  Exiting...')
            return results

        self.import_collections(available_collections)

        return results
