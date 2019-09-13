import logging
import traceback
from functools import lru_cache
from cabby import create_client
from connectors.taxii.stix_parse import sanitize_stix, parse_stix, BINDING_CHOICES
from connectors.taxii.feed_helper import FeedHelper
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
    reports_limit: int = 10000
    fail_limit: int = 10   # num attempts per collection for 
                           # polling server and parsing stix content


class TaxiiConnector(Connector):
    Config = TaxiiConfig
    name = "taxii"


    # TODO: better exception handling
    def create_taxii_client(self):
        self.client = None
        try:
            conf = self.config
            client = create_client(conf.site,
                                   use_https=conf.use_https,
                                   discovery_path=conf.discovery_path)
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

        except Exception as e:
            log.info(e.message)


    def create_uri(self, config_path):
        uri = None
        if config_path and self.config.site:
            if self.config.use_https:
                uri = 'https://'
            else:
                uri = 'http://'
            uri = uri + self.config.site + config_path
        return uri        


    # TODO: better exception handling
    def query_collections(self):
        collections = []
        try:
            uri = self.create_uri(self.config.collection_management_path)
            collections = self.client.get_collections(uri=uri) # autodetect if uri=None
            for collection in collections:
                log.info(f"Collection Name: {collection.name}, Collection Type: {collection.type}")
        except Exception as e:
            log.info(e.message)
        return collections


    def poll_server(self, collection, feed_helper):
        content_blocks = []
        uri = self.create_uri(self.config.poll_path)
        try:
            log.info(f"Polling Collection: {collection.name}")
            content_blocks = self.client.poll(uri=uri,
                                         collection_name=collection.name,
                                         begin_date=feed_helper.start_date,
                                         end_date=feed_helper.end_date,
                                         content_bindings=BINDING_CHOICES)
            log.debug(f"content_blocks: {content_blocks}")
        except Exception as e:
            log.warning(f"problem polling taxii server: {e.message}")
        return content_blocks


    def parse_collection_content(self, content_blocks):
        reports = []
        for block in content_blocks:
            reports.extend(parse_stix(block.content, self.config.default_score))
        return reports


    def import_collection(self, collection):
        num_fail = 0
        reports = []
        reports_limit = self.config.reports_limit
        feed_helper = FeedHelper(self.config.start_date,
                                 self.config.minutes_to_advance)

        while feed_helper.advance():  
            content_blocks = self.poll_server(collection, feed_helper)  
            _reports = self.parse_collection_content(content_blocks)
            if not _reports:
                num_fail += 1
            else:
                reports.extend(_reports)
            if len(reports) > reports_limit:
                log.info("We have reached the reports limit of {reports_limit}")
                break
            if collection.type == 'DATA_SET': # data is unordered, not a feed
                log.info(f"collection:{collection}; type data_set, not advancing feed")
                break 
            if num_fail > self.config.fail_limit:   # to prevent infinite loop
                log.error('Max fail limit reached; Exiting.')
                break            

        if len(reports) > reports_limit:
            log.info("Truncating reports to length {reports_limit}")
            reports = reports[:reports_limit]
        return reports
            

    def import_collections(self, available_collections):
        desired_collections = self.config.collections
        desired_collections = [x.strip() for x in desired_collections.lower().split(',')]
        
        want_all = False
        if '*' in desired_collections:
            log.debug('desired collections: *')
            want_all = True

        reports = []
        for collection in available_collections:
            if collection.type != 'DATA_FEED' and collection.type != 'DATA_SET':
                log.debug(f"collection:{collection}; type not feed or data")
                continue
            if not collection.available:
                log.debug(f"collection:{collection}; not available")
                continue
            if want_all or collection.name.lower() in desired_collections:
               reports.extend(self.import_collection(collection))

        return reports
       
    
    def format_report(self, report, binary): 
        try:
            analysis_name = f"{report['title']};{report['id']}" 
            scan_time = report['timestamp']
            score = report['score']
            link = report['link']
            #TODO: we wasted report['description'] with this interface
            ioc_dict = report['iocs']
            result = self.result(binary,
                                 analysis_name=analysis_name,
                                 scan_time=scan_time,
                                 score=score)
            for ioc_key, ioc_val in ioc_dict.items():
                result.ioc(values=ioc_val, field=ioc_key, link=link)
        except Exception as e:
            log.info(e.message)
            result = self.result(binary, analysis_name="exception_format_report", error=True)
        return result


    def analyze(self, binary, data):   # TODO:ignoring binary for now
        self.create_taxii_client()  # TODO: make this part of init, not analyze
                                    # assuming analyze is called repeatedly
        if not self.client:
            log.error('Unable to create taxii client.  Exiting...')
            return [self.result(binary, analysis_name="exception_taxii_client", error=True)]
        
        available_collections = self.query_collections()
        if not available_collections:
            log.warning('Unable to find any collections.  Exiting...')
            return [self.result(binary, analysis_name="exception_query_collections", error=True)]

        reports = self.import_collections(available_collections)
        if not reports:
            log.warning('Unable to import collections.  Exiting...')
            return [self.result(binary, analysis_name="exception_import_collections", error=True)]
            
        results = []
        for report in reports:
            results.append(self.format_report(binary, report))
        return results
