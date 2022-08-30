from typing import Union
from elasticsearch import ConnectionTimeout


try:
    from elasticsearch import Elasticsearch
    from elasticsearch.helpers import streaming_bulk, BulkIndexError
    from elastic_transport import ObjectApiResponse
    from requests import head
    from unicodedata import normalize
    from math import ceil
    from credentials import es_cert, es_user, es_password
    # from helper_es_index_settings import ANALYZERS, MAPPINGS
except ImportError as error:
    print(error)

class ES:
    """
    Provides ElasticSearch interactivity
    
    Methods
    -------
    - check_connection() -> ObjectApiResponse/bool : begins a sequence to verify (and redownload) drs_metadata
    - indices() -> list/bool : retrieves all indices (excluding hidden ones) from ElasticSearch
    - del_index(index=str) -> ObjectApiResponse : deletes an index (including contents, shards and metadata)
    - add_index(index=str) -> ObjectApiResponse : add an index (with specific settings)
    - add_doc(index=str, doc=dict) -> ObjectApiResponse : add document to an index
    - save(data=dict) -> Generator : bulk insert records into ElasticSearch
    - build_library -> Generator : compile records for the 'library' on the site and bulk insert into ElasticSearch

    Private Methods
    - __update(docs=dict, fn=function) : adds data to ElasticSearch
    
    """

    def __init__(self):
        """
        Establishes a connection to ElasticSearch        
        """
        self.es = Elasticsearch(f'https://localhost:443', ca_certs=es_cert, basic_auth=(es_user, es_password), request_timeout=60)
        self.es.transport.retry_on_timeout = True
        self.es.transport.max_retries=10

    def check_connection(self) -> Union[ObjectApiResponse, bool]:
        """
        Checks access to ElasticSearch by requesting server info

        Returns
        -------
        - ObjectApiResponse : response from ElasticSearch
        #### OR
        - Boolean : False if failed
        """
        try:
            return self.es.info()
        except:
            return False

    def indices(self) -> Union[list, bool]:
        """
        Retrieves all indices (excluding hidden ones) from ElasticSearch

        Returns
        -------
        - list : a list of index names
        #### OR
        - Bool : False if failed

        Error Handling
        --------------
        - Raises Exception

        """
        try:
            return self.es.indices.get_alias(expand_wildcards=['open']).body
        except:
            return False

    def del_index(self, index:str) -> ObjectApiResponse:
        """
        Deletes an index (including contents, shards and metadata)
        
        Parameters
        ----------
        - index (str) : name of index to delete

        Returns
        -------
        - ObjectApiResponse : response from ElasticSearch

        Error Handling
        --------------
        - Raises Exception
        """
        try:
            return self.es.options(ignore_status=[400, 404]).indices.delete(index=index)
        except Exception as e:
            raise e

    def add_index(self, index:str) -> ObjectApiResponse:
        """
        Adds a new index with a settings object

        Parameters
        ----------
        - index (str) : name of index to add

        Returns
        -------
        - ObjectApiResponse : response from ElasticSearch
        """

        def settings(index:str) -> dict:
            
            def fields(index:str):
                if index == 'iiif':
                    return {
                        "manifest.sequences.canvases.metadata.Value" : {
                            "type" : "text"
                        }
                    }
                else:
                    # ITERATE OVER ALL PROPERTIES AND ADD A .keyword_field property for every field
                    
                    return {
                        "RelatedItems" : {
                            "type" : "nested"
                        }
                    }
            
            return { 
                "settings" : {
                    "analysis" : {
                        "filter" : {},
                        "analyzer" : {
                            "synonym_keyword": {
                                "tokenizer": "keyword",
                                "filter": [
                                    "asciifolding",
                                    "lowercase",
                                    "synonym"
                                ]
                            },
                            "synonym_pattern": {
                                "tokenizer": "pattern",
                                "filter": [
                                    "asciifolding",
                                    "lowercase",
                                    "synonym"
                                ]
                            }
                        },
                        "filter": {
                            "synonym": {
                                "type": "synonym",
                                "synonyms_path": f'analysis/{index}.txt'
                            }
                        }
                    }
                },
                "mappings" : {
                    "properties" : fields(index)
                }
            }
        
        return self.es.indices.create(index=index, **settings(index))

    def add_doc(self, index:str, doc:dict) -> ObjectApiResponse:
        """
        Adds a document to an index

        Parameters
        ----------
        - index (str) : name of index to add to
        - doc (dict) : dictionary with document data
        
        Returns
        -------
        - ObjectApiResponse : response from ElasticSearch

        Error Handling
        --------------
        - Raises Exception
        """
        try:
            return self.es.index(index=index, document=doc)
        except Exception as e:
            raise e

    def save(self, manifests:dict) -> dict:
        """
        Generator function that batch processes data for writing to ElasticSearch in batches of 5000.

        NOTE:   Connection time-out may occur if chunk_size is set too high and/or request_timeout too low. 
                If the process stalls this will inadvertently interrupt the insertion process. In that case, 
                the safest option is to simply restart the program. Also note that documents are indexed upon 
                insertion, which may take long depending on complexity of document (for that reason this program
                removes extraneous data from each record). The refresh parameter on the streaming_bulk API 
                prevents indices not to be ready for querying and needs to be set to 'wait_for' to make sure 
                the build_library method is able to request all documents in the publisheddocuments index.

        Parameters
        ----------
        - data (dict) : the dictionary with compiled resources to push to ElasticSearch

        Yields
        ------
        - result (dict) : result of streaming insert operation

        Error Handling
        --------------
        - Raises Exception
        - Raises BulkIndexError
        - Raises ConnectionTimeout
        """
        try:
            
            indices = list(set([v['ES_index'] for v in manifests.values()]))
            
            if self.es.ping():

                for index in indices:
                    self.del_index(index)
                    self.add_index(index)

                try:
                    try:
                        def data_generator(manifests):
                            for v in manifests.values():
                                yield {
                                "_index" : v['ES_index'],
                                "_id" : f'{v["ES_index"]}-{v["RecID"]}',
                                **v
                            }

                        size = 10000

                        for ok, result in streaming_bulk(self.es, data_generator(manifests), chunk_size=size, request_timeout=60, refresh='wait_for'):
                            if ok is not True:
                                print(str(result))
                            else:
                                yield result
                    except ConnectionTimeout as e:
                        size = size - 500
                except BulkIndexError as e:
                    raise e
            else:
                print(self.es.info())
        except Exception as e:
            raise e
    
    def build_library(self) -> dict:
        """
        Builds a 'library' of published documents with PDFs only, grouped by author.
        Uses the class save-function to bulk-insert the library into ElasticSearch.

        Yields
        ------
        dict : result of streaming insert operation

        """

        published_query = { 
            "query": {
                "bool": {
                    "must": {
                        "exists": {
                            "field": "doc.PDF"
                        }
                    },
                    "must_not": {
                        "term": {
                            "doc.PDF": ""
                        }
                    }
                }
            },
            "size" : 1000
        }

        documents = self.es.search(index='publisheddocuments', body=published_query)['hits']['hits']

        library = {}

        def fileSize(file):
            fileSize = head(file).headers["content-length"]
            if fileSize.isdigit():
                fileSize = int(fileSize)
                fileSize = f'{ceil(fileSize / 1000)} KB' if fileSize <= 999999 else f'{round(fileSize / 1000000, 2)} MB'
            return fileSize

        def organizeData():

            for result in documents:
                result = result['_source']
                
                if len(result['Authors']): 
                    for author in result['Authors']:
                        if author['ConstituentID'] not in library: 
                            library[author['ConstituentID']] = []
                            library['ES_index'] = 'library'

                        title = str(normalize('NFD', result['Title']).encode('ascii', 'ignore').decode("utf-8"))
                        sortText = result['Notes'] if result['Notes'] is not None else title
                        sortText = str(normalize('NFD', sortText).encode('ascii', 'ignore').decode("utf-8"))
                        
                        library[author['ConstituentID']].append({
                            'Author' : author['DisplayName'],
                            'Title' : title,
                            'AlphaSort' : str(normalize('NFD', author['AlphaSort']).encode('ascii', 'ignore').decode("utf-8")),
                            'DisplayText' : str(normalize('NFD', result['BoilerText']).encode('ascii', 'ignore').decode("utf-8")),
                            'SortText' : sortText,
                            'Format' : result['Format'],
                            'FileSize' : fileSize(result['PDF']),
                            'URL' : result['PDF']
                        })

        organizeData()

        yield self.save(library)