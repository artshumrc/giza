from helper_logger import Logger

from cursor_FSS import file_open, file_del, file_save, get_thumbnails, save_thumbnails
from cursor_TMS import get_drs_metadata
from helper_thumbnailer import download_thumbnails
from module_iiif_worker import check_drs

from module_iiif_worker import IIIF_Worker
from module_MET_worker import MET_Worker
from module_sites_worker import Sites_Worker
from module_objects_worker import Objects_Worker
from module_constituents_worker import Constituents_Worker
from module_published_worker import Published_Worker
from module_media_worker import Media_Worker

overall_progress = {}

class Module(object):
    """
    This class performs the main operations per module.
    
    Methods
    -------
    - check_connection() : begins a sequence to verify (and redownload) drs_metadata # this doesn't exist? Got moved to cursor?
    - indices() : retrieves all indices (excluding hidden ones) from ElasticSearch
    - del_index(index=str) : deletes an index (including contents, shards and metadata)
    # - add_index(index=str, doc=dict) : add document to an index
    - bulk_insert(index=list, data=list) : Overwrites the contents of an index
    - bulk_update(indices=list, fn=function) : start ElasticSearch bulk update sequence
    - build_mapping(data=list -> dict) : dynamically builds an ElasticSearch mapping for a new index
    
    
    - check_drs() : begins a sequence to verify (and redownload) drs_metadata
    - check_records() : checks if the tables are ready and accessible
    - process() : calls the main methods for each module
    - add_manifests() : generate manifests for each document type
    - save() : save compiled data to ElasticSearch
    """
    def __init__(self, modules, module_type, cursor, drs, memory, push, tables, store, thumbnails, thumbnails_refresh, refresh, compile, es):
        """
        Parameters
        ----------
        - module_type (str) : the name of the module
        - cursor (Cursor) : the cursor with (in)active connection to ES/TMS
        - store (bool) : store compilations to disk
        - refresh (bool) : force refresh of local JSON tables
        - compile (bool) : force compilation with local JSON tables
        - es (bool) : force push to ElasticSearch
        """
        self.logger = Logger(module_type)

        self.modules = modules
        self.module_type = module_type
        
        self.cursor = cursor

        self.drs = drs
        self.memory = memory
        self.push = push
        self.tables = tables
        self.store = store
        self.thumbnails = thumbnails
        self.thumbnails_refresh = thumbnails_refresh
        self.refresh = refresh
        self.compile = compile
        self.es = es

        self.files = get_thumbnails() if self.thumbnails else []

        self.data = []
        self.relations = []
        self.thumbnail_urls = {}
        self.counter = 1

        self.logger.log(f'*** STARTING {module_type.upper()} MODULE ***', module_type)

        if self.memory:
            self.logger.log(f'>>> PROCESSING IN MEMORY ', module_type)

        overall_progress[module_type] = {}

        def clear_tables():
            """
            Clear the local JSON tables
            """

            try:
                file_del(self.module_type, 'tables', exclude=['drs'] if self.drs else [])
            except:
                raise

        def rebuild():
            """
            Clear the local JSON compilations
            """
            
            try:
                file_del(module_type, 'compiled', module_type)

                if module_type == 'iiif': self.check_drs()

            except:
                raise

        if self.refresh: clear_tables()
        if self.refresh or self.compile: rebuild()
        
        try:
            # THE COMPILED FILE DOES NOT EXISTS OR IS LIKELY CORRUPT
            if not file_open('compiled', module_type, module_type, False):
                rebuild()

            self.check_records()
            
            return
        except:
            raise

    def check_drs(self):
        """
        Checks if the drs metadata are available and initiates download if not
        """
        
        drs_metadata = check_drs(self.cursor.tms)

        if type(drs_metadata) is list:
            self.logger.log('>>> DOWNLOADING IIIF METADATA FROM DRS (THIS CAN TAKE A GOOD TEN MINUTES)', self.module_type)
            file_save('tables', 'drs', get_drs_metadata(drs_metadata), 'iiif')

    def check_records(self):
        """
        Checks if the records are complete: tables and compilations resulting from the tables.
        If not, will initiate download and/or compilation of files. After processing, records
        are stored to disk and/or pushed to ElasticSearch.
        """
        
        try:

            # TRY REFRESH OF LOCAL JSON TABLES
            if self.refresh:
                first_record, data = self.cursor.tms.tables(module=self.module_type, tables=self.tables)
                self.compiled_data, self.relations, self.thumbnail_urls, log_results = self.process(first_record, data)
                self.logger.log(f'>>> LOGGING RESULTS', self.module_type, results=log_results)

            self.logger.log(f'>>> CHECKING "{self.module_type.upper()}" COMPILATIONS', self.module_type)

            if file_open('compiled', self.module_type, self.module_type, False) and file_open('compiled', 'relations', self.module_type, False):
                self.logger.log(f'>>> USING "{self.module_type.upper()}" COMPILATIONS FROM FILE', self.module_type)
                self.compiled_data = file_open('compiled', self.module_type, self.module_type, True)
                self.relations = file_open('compiled', 'relations', self.module_type, True)
                self.logger.log(f'>>> "{self.module_type.upper()}" COMPILATIONS CONFIRMED', self.module_type)
            else:
                self.logger.log(f'>>> NO EXISTING "{self.module_type.upper()}" COMPILATIONS FOUND', self.module_type)

                # USE TABLES TO BUILD NEW COMPILATIONS
                first_record, data = self.cursor.tms.tables(module=self.module_type, tables=self.tables)
                self.compiled_data, self.relations, self.thumbnail_urls, log_results = self.process(first_record, data)
                self.logger.log(f'>>> LOGGING RESULTS', self.module_type, results=log_results)

            if 'iiif' in self.module_type or 'met' in self.module_type: self.compiled_data = self.relations

            if self.memory:
                overall_progress[self.module_type] = { 'compilation' : self.compiled_data, 'relations' : self.relations, 'thumbnails' : self.thumbnail_urls }

            if self.thumbnails and self.module_type not in ['iiif', 'met']:

                thumbnail_urls = [val for val in self.thumbnail_urls.values()]

                # THE GOAL IS TO SKIP DOWNLOADING THUMBNAILS ALREADY IN SELF.FILES

                # CHECK URLS AGAINST THOSE ALREADY IN THE STATIC FOLDER
                if not self.thumbnails_refresh and len(self.files):
                    
                    # GET ALL THUMBNAIL IDS FOR THIS MODULE
                    thumbnail_ids = [drs_id['Thumbnail_ID'] for drs_id in thumbnail_urls]

                    # THIS IS WHAT WE SHOULD HAVE ON DISK
                    save_thumbnails(self.module_type, thumbnail_ids)

                    # CHECK WHAT'S ACTUALLY ON DISK
                    thumbnails = get_thumbnails(self.module_type)

                    # COMPARE IDS FROM THE MODULE WITH THOSE ON DISK
                    remaining_ids = list(set(thumbnail_ids) - set(thumbnails))

                    check_list = { x['Thumbnail_ID'] : x['url'] for x in thumbnail_urls }

                    thumbnail_urls = []

                    for idx in remaining_ids:
                        if idx in check_list:
                            thumbnail_urls.append({ 'Thumbnail_ID' : idx, 'url' : check_list[idx]['url'] })

                # DOWNLOAD LEFTOVERS
                if len(thumbnail_urls) > 0:
                    self.logger.log(f'>>> DOWNLOADING {len(thumbnail_urls)} NEW THUMBNAILS FOR "{self.module_type.upper()}"', self.module_type)
                    res, error = download_thumbnails(thumbnail_urls)
                    self.logger.log(f'>>> {len(error)} ERRORS DOWNLOADING THUMBNAILS FOR "{self.module_type.upper()}"', self.module_type)

                    # UPDATE THE LOG ON DISK
                    save_thumbnails(self.module_type, thumbnail_ids)

                    # SUBTRACT ALL DOWNLOADS FROM SELF.FILES
                    # self.files = list(set(self.files) - set(thumbnail_ids))
    
                    # SAVE SELF.FILES TO SPEED UP THE NEXT MODULE
                    # file_save(f'static/images/thumbnails', 'thumbnails', self.files)

                else:
                    self.logger.log(f'>>> NO NEW THUMBNAILS FOR MODULE "{self.module_type.upper()}"', self.module_type)

            # BULK UPDATE MANIFESTS (EXCEPT IIIF, MET, PUBLISHED AND MEDIA)
            if self.module_type not in ['iiif', 'met', 'published', 'media']: self.add_manifests()

            # BULK WRITE COMPILATIONS TO FILE (COSTLY OPERATION)
            if self.store:
                self.logger.log(f'>>> WRITING "{self.module_type.upper()}" COMPILATIONS TO DISK', self.module_type)
                file_save('compiled', self.module_type, self.compiled_data, self.module_type)
                file_save('compiled', 'relations', self.relations, self.module_type)

            # PUSH ALL DATA TO ELASTICSEARCH IN ONE GO AT THE VERY END, IF SO DESIRED
            if self.es:
                
                if self.push:
                    if self.module_type in self.modules[-1:]:
                        for module, data in overall_progress.items():
                            if module not in ['met']:
                                self.write(module, data)
                else:
                    # BULK INSERT RECORDS TO ES (EXCEPT MET)
                    if 'met' not in self.module_type:
                        if self.module_type == 'iiif': self.relations = overall_progress['iiif']['compilation']
                        self.write(self.module_type, { 'compilation' : self.compiled_data })
                        self.write('iiif', { 'compilation' : self.relations })

            self.logger.log(f'*** {self.module_type.upper()} MODULE FINISHED ***', self.module_type)

        except:
            raise

    def write(self, module, data):
        self.save(module, data['compilation'])
        if module == 'published':
            self.logger.log(f'>>> DEVELOPING LIBRARY', self.module_type)
            results = 0
            for res in self.cursor.es.build_library():
                if res:
                    results = results + 1
                    self.logger.log(f'>>> WRITTEN DOCS: {results}', 'library', end=True)

    def process(self, first_record:list, data:list):
        """
        Processing the first records and all subsequent data. First_record contains the top-level object
        for each module and is passed to the constructor for each individual worker to be processed in the
        'build'-method. Upon completion of the 'build'-method the worker's 'start'-method is called, which
        in turn, processes all subsequent data. For most operations that is a multithreading operation, which
        significantly speeds up all data processing.

        Parameters
        ----------
        - first_record (list) : the top-level query that needs to be executed and processed first
        - data : the remained of all data for this module to be processed
        
        Returns
        -------
        - tuple : the results of the processing operations in the worker's 'start'-method

        Raises
        ------
        - ModuleNotFoundError : there was a problem with this worker
        """

        try:
            self.logger.log(f'>>> PREPARING "{self.module_type.upper()}" RECORDS FOR NEW BUILD', self.module_type)

            if 'iiif' in first_record['key']: worker = IIIF_Worker(first_record['rows'], first_record['cols'], data).build_iiif()
            if 'met' in first_record['key']: worker = MET_Worker(first_record['rows'], first_record['cols'], data).build_MET()           
            if 'sites' in first_record['key']: worker = Sites_Worker(first_record['rows'], first_record['cols'], data).build_sites()
            if 'objects' in first_record['key']: worker = Objects_Worker(first_record['rows'], first_record['cols'], data).build_objects()
            if 'constituents' in first_record['key']: worker = Constituents_Worker(first_record['rows'], first_record['cols'], data).build_constituents()
            if 'published' in first_record['key']: worker = Published_Worker(first_record['rows'], first_record['cols'], data).build_published()
            if 'media' in first_record['key']: worker = Media_Worker(first_record['rows'], first_record['cols'], data).build_media()
            return worker.start()

        except Exception as e:
            print(e)
            raise e

    def build_manifest_canvas(self, manifest_id:str, drs_id:str, idx:int, resource:dict, label:str, metadata):
        """
        Constructs a canvas for a manifest

        Parameters
        ----------
        - manifest_id (str) : the identifier for the manifest
        - drs_id (str) : the identifier in drs
        - idx (int) : a sequence number
        - resource : a manifest generated for the provided drs_id 
        - label : a label to go with this canvas
        - metadata : metadata

        Returns
        -------
        - dict : canvas
        """

        drs_metadata = file_open('compiled', 'drs', 'iiif', True)

        def build_resource(drs_id):
            """
            Builds a manifest for the provided drs_id

            Parameters
            ----------
            - drs_id (str) : the identifier in drs

            Returns
            -------
            - dict : manifest resource
            """
            return {
                "width": drs_metadata[drs_id]['width'],
                "@id": f'https://ids.lib.harvard.edu/ids/iiif/{drs_id}/full/full/0/default.jpg',
                "@type": "dctypes:Image",
                "height": drs_metadata[drs_id]['height'],
                "service": {
                    "@context": "https://iiif.io/api/presentation/2/context.json",
                    "@id": f'https://ids.lib.harvard.edu/ids/iiif/{drs_id}',
                    "profile": "http://iiif.io/api/image/2/level1.json"
                }
            }

        if resource is None: resource = build_resource(drs_id)

        canvas = {
            "@id": f'{manifest_id}/canvas/{idx}',
            "label": label if label else str(idx+1),
            "@type": "sc:Canvas",
            "width": resource['width'],
            "height": resource['height'],
            "images": [
                {
                    "on": f'{manifest_id}/canvas/{idx}',
                    "motivation": "sc:painting",
                    "@type": "oa:Annotation",
                    "@id": f'{manifest_id}/annotation/canvas/{idx}',
                    "resource": resource
                }
            ]
        }

        if metadata: 
            canvas['metadata'] = metadata

        return canvas

    def build_base_manifest(self, manifest_id, data):
        """ This method returns the base parameters for an IIIF manifest. All subsequent methods will add to the resulting object from this method. """
        ob = {
            "description": data['Description'],
            "@context": "https://iiif.io/api/presentation/2/context.json",
            "@id": f'{manifest_id}',
            "label": data['Label'],
            "@type": "sc:Manifest"
        }
        if 'Metadata' in data: ob['metadata'] = data['Metadata']
        return ob

    def generate_multi_canvas_iiif_manifest(self, manifest_id, data):
        """ Compile all the resources associated with a site into one manifest """

        def build_multi_image_sequence(manifest_id, resources_list, drs_ids, canvas_labels, canvas_metadatas):
            """ return sequence list of canvases each with one image """
            seq_id = f'{manifest_id}/sequence/0'
            seq = [
                {
                    "label": "Default order",
                    "@type": "sc:Sequence",
                    "@id": seq_id,
                    "canvases": []
                }
            ]
            for idx, resource in enumerate(resources_list):

                # TRIGGERS RECURSION
                seq[0]['canvases'].append(self.build_manifest_canvas(manifest_id, drs_ids[idx], idx, resource, canvas_labels[idx], canvas_metadatas[idx]))
            return seq

        manifest = self.build_base_manifest(manifest_id, data)
        manifest["sequences"] = build_multi_image_sequence(manifest_id, data['Resources'], data['DRS_IDs'], data['Canvas_labels'], data['Canvas_metadatas'])
        for canvas in manifest["sequences"][0]["canvases"]:
            if "startCanvas" in data and data["startCanvas"] in canvas["images"][0]["resource"]["service"]["@id"]:
                manifest["sequences"][0]["startCanvas"] = canvas["@id"]
        return manifest

    def add_manifests(self):
        """
        Checks if records are complete: tables and compilations resulting from the tables.
        If not, will initiate download and/or compilation of files.
        """
        try:
            self.logger.log(f">>> COMPILING RESOURCES FOR {self.module_type.upper()}", self.module_type)

            manifests = overall_progress['iiif']['compilation'] if self.memory else file_open('compiled', 'iiif', 'iiif', True)
            relations = overall_progress[self.module_type]['relations'] if self.memory else file_open('compiled', 'relations', self.module_type, True)
            
            # UPDATING THE MANIFESTS
            for manifest_id, v in relations.items():
                manifest_id = "-".join([self.module_type.title(), manifest_id.split('-')[1]])
                manifest = {                    
                    "RecID": manifest_id,
                    "manifest": self.generate_multi_canvas_iiif_manifest(manifest_id, v),
                    'ES_index' : 'iiif'
                }

                # if manifest_id in manifests:
                    # print('manifest needs updating instead?')
                
                manifests[manifest_id] = manifest
            
            self.logger.log(f">>> ADDED {len(relations)} MANIFESTS FOR {self.module_type.upper()}", self.module_type)

            overall_progress['iiif']['compilation'] = manifests

            # SAVE FINAL MANIFESTS TO DISK
            if self.store: file_save('compiled', 'iiif', manifests, 'iiif')

            # THE LAST MODULE TO ADD MANIFESTS IS PUBLISHED AND SHOULD SAVE THE MOST COMPLETE ITERATION OF ALL MANIFESTS TO ELASTICSEARCH
            if 'published' in self.module_type:
                
                # WE MAKE SURE THE MOST RECENT MANIFESTS ARE WRITTEN TO ELASTICSEARCH
                overall_progress['iiif']['compilation'] = manifests
                
        except:
            print('problem updating manifests!')

    def save(self, module:str, data:dict):
        try:
            self.logger.log(f'>>> WRITING {len(data)} {module.upper()} DOCUMENTS TO ELASTICSEARCH', self.module_type)
            results = 0
            for res in self.cursor.es.save(data):
                if res:
                    results = results + 1
                    self.logger.log(f'>>> WRITTEN DOCS: {results}', self.module_type, end=True)
        except Exception as e:
            raise e