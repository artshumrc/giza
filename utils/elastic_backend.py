from django.conf import settings
# Django 2.2.24:
# from django.utils.six.moves.urllib.parse import urlparse

# Django 3:
from urllib.parse import urlparse

from elasticsearch import Elasticsearch
# from elasticsearch.helpers import scan
import environ
env = environ.Env()
environ.Env.read_env()

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
        })

ES_INDEX = ES_BACKEND.pop('INDEX', 'giza')
ES_TIMEOUT = ES_BACKEND.pop('TIMEOUT', 5)

# TODO: refactor and move all config to settings.py
ES_CERT = env('ELASTICSEARCH_CERT')
ES_USER = env('ELASTICSEARCH_USER')
ES_PASSWORD = env('ELASTIC_PASSWORD')

es = Elasticsearch(hosts=ES_HOSTS, ca_certs=ES_CERT, basic_auth=(ES_USER, ES_PASSWORD), request_timeout=30)
es.transport.max_retries=10
es.transport.retry_on_timeout=True