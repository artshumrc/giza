from django.conf import settings
# Django 2.2.24:
# from django.utils.six.moves.urllib.parse import urlparse

# Django 3:
from urllib.parse import urlparse


from elasticsearch import Elasticsearch
# from elasticsearch.helpers import scan

ES_BACKEND = getattr(settings, 'SEARCH_BACKENDS').get('default')

ES_HOSTS = ES_BACKEND.pop('HOSTS', None)
ES_URLS = ES_BACKEND.pop('URLS', ['localhost:9200'])
ES_HOSTS
if ES_HOSTS is None:
    ES_HOSTS = []

    for url in ES_URLS:
        parsed_url = urlparse(url)

        use_ssl = parsed_url.scheme == 'https'
        port = parsed_url.port or (443 if use_ssl else 80)

        http_auth = None
        if parsed_url.username is not None and parsed_url.password is not None:
            http_auth = (parsed_url.username, parsed_url.password)

        ES_HOSTS.append({
            'host': parsed_url.hostname,
            'port': port,
            'url_prefix': parsed_url.path,
            'use_ssl': use_ssl,
            'http_auth': http_auth,
        })

ES_INDEX = ES_BACKEND.pop('INDEX', 'giza')
ES_TIMEOUT = ES_BACKEND.pop('TIMEOUT', 5)

# TODO: THESE VARIABLES SHOULD COME FROM A SAFE PLACE
ES_HOSTS = f'https://localhost:9200'
es_user = 'elastic'
es_password = '0xlEM4BduYCAHCE3XaKH'
es_cert = 'D:\elasticsearch-8.1.2\config\certs\http_ca.crt'

es = Elasticsearch(hosts=ES_HOSTS, ca_certs=es_cert, basic_auth=(es_user, es_password))