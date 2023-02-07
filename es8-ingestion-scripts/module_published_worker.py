from concurrent.futures import ThreadPoolExecutor, wait
from operator import itemgetter
from re import sub, compile, match, IGNORECASE
from base import Base

class Published_Worker(Base):
    """
    Sub-class of Base for the 'published' base setup. 
    
    NOTE: Published include published scholarship related to Giza
    
    Methods
    -------
    - build_published() -> Published_Worker : builds the basic object JSON record
    - start() -> dict, dict : the start method of the Published_Worker module
    - media(rows=list) -> dict : adds a primary display to the record
    - constituents(rows=list) -> dict : updates and adds constituents to items in the RelatedItems property
    """
    def __init__(self, rows, cols, data=None, cpu_workers:int=2):
        super().__init__('published')
        
        self.rows = rows
        self.cols = cols
        self.data = data
        self.cpu_workers = cpu_workers

    def build_published(self):
        """
        Transforms the top-level record to a JSON format.

        Parameters
        ----------
        None

        Returns
        -------
        - self (Published_Worker) : the instance of the class used by Module to call the worker method on this instance Base class
        """
        
        # CONVERT ROWS TO DICTS; COL VALUES: RecID, Number
        new_rows = [{ y : row[self.cols.index(y)] for y in self.cols } for row in self.rows ]

        for row in new_rows:
            row = self.sanitize(row)

            row = { k : v.title() if type(v) == str and v.isupper() and match(r'\A[\w-]+\Z', v) else v for k, v in row.items() } # Title single words

            clean = compile('</?font.*?>', IGNORECASE)
            row = { k : sub(clean, '', v) if type(v) == str else v for k, v in row.items() }                                     # REMOVE <FONT> TAGS
            row = { k : None if ('BeginDate' in k or 'EndDate' in k) and v == 0 else v for k, v in row.items() }
            
            row['DisplayText'] = row['Title']
            row['Roles'] = []
            row['Authors'] = []
            row['ES_index'] = 'publisheddocuments'
            self.records[str(row['RecID'])] = row
               
        return self

    def start(self):
        """
        The start method of the Published_Worker module, relying on multithreading, calls the 
        following local and Base methods simultaneously:
        1) Sites (Base)
        2) Media (local)
        3) Objects (Base)
        4) Constituents (local)

        Returns
        -------
        - self.records (dict) : data relevant to generation of published records
        - self.relations (dict) : data relevant to manifest generation derived from the published records
        - dict : processing results
        """
        with ThreadPoolExecutor(self.cpu_workers) as executor:
            for rows in self.data:

                # CONVERT ROWS TO DICTS
                row = [{ y : row[rows['cols'].index(y)] for y in rows['cols'] } for row in rows['rows']]

                # CONSTITUENTS TASKS
                if 'published_sites' in rows['key']: self.futures.append(executor.submit(self.sites, row))
                if 'published_media' in rows['key']: self.futures.append(executor.submit(self.media, row))
                if 'published_objects' in rows['key']: self.futures.append(executor.submit(self.objects, row))
                if 'published_constituents' in rows['key']: self.futures.append(executor.submit(self.constituents, row))

            done, not_done = wait(self.futures)
           
            res, err = {}, {}

            for future in done:
                result = future.result()
                method = list(result.keys())[0]
                res[method] = { 'res' : { 'summary' : len(result[method]['res']), 'res' : result[method]['res'] }}
                err[method] = { 'err' : { 'summary' : len(result[method]['err']), 'err' : result[method]['err'] }}

            return self.records, self.relations, self.thumbnail_urls, { 'published_worker_res' : res, 'published_worker_err' : err }

    def media(self, rows:list):
        """
        Adds a primary display to the record. These records are kept in self.records on the class.

        Parameters
        ----------
        - rows (list) : a list of dictionaries with data to be applied to the class' records variable

        Returns
        -------
        - dict : processing results
        """
        res, err = [], []
        
        for row in rows:
            try:
                main_url = self.get_media_url(row['MainPathName'], row['MainFileName'])

                self.records[row['RecID']]['PrimaryDisplay'] = {
		            'Thumbnail' : self.get_media_url(row['ThumbPathName'], row['ThumbFileName']),
		            'Main' : main_url
		        }

                self.records[row['RecID']]['PDF'] = main_url if len(main_url) else None
                
                res.append(f'Published-{row["RecID"]}')
            except:
                err.append(f'Published-{row["RecID"]}')

        return { 'published_worker_media' : { 'res' : res, 'err' : err } }

    def constituents(self, rows:list):
        """
        Updates and adds constituents to items in the RelatedItems property. These records are kept in self.records on the class.

        Parameters
        ----------
        - rows (list) : a list of dictionaries with data to be applied to the class' records variable

        Returns
        -------
        - dict : processing results
        """
        res, err = [], []
      
        for row in rows:
            try:
                if 'RelatedItems' not in self.records[row['RecID']]: self.records[row['RecID']]['RelatedItems'] = {}
                if "PublishedDocuments" not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems']['PublishedDocuments'] = []

                if 'ConstituentTypeID' in row: thumbnail_id = f'{self.constituenttypes.get(int(row["ConstituentTypeID"]))}-{row["RecID"]}'
                
                drs_id = None if row['ArchIDNum'].lower() == "null" else row['ArchIDNum']

                if drs_id:
                    thumbnail_url = self.thumbnail_url(drs_id)

                if drs_id.lower() == "null" or not drs_id:
                    thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])

                if len(thumbnail_url) and thumbnail_id not in self.thumbnail_urls:
                    self.thumbnail_urls[thumbnail_id] = { 'Thumbnail_ID' : thumbnail_id, 'url' : thumbnail_url }

                # thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])
                
                # if not thumbnail_url and drs_id: thumbnail_url = self.thumbnail_url(drs_id)

                # if thumbnail_url:
                    # self.thumbnail_urls.append({ 'drs_id' : drs_id, 'url' : thumbnail_url })

                if row['Role'] not in self.records[row['RecID']]['Roles']: self.records[row['RecID']]['Roles'].append(row['Role'])
                if row['Role'] == "Author": 
                    self.records[row['RecID']]["Authors"].append(row)
                
                constituent_dict = {
                    'RecID' : row['ConstituentID'],
                    'Role' : row['Role'],
                    'DisplayName' : row['DisplayName'],
                    'DisplayDate' : row['DisplayDate'] if row['DisplayDate'] != "NULL" else "",
                    'DisplayText' : row['DisplayName'],
                    'Description' : row['Remarks'] if row['Remarks'] != "NULL" else "",
                    'Thumbnail' : thumbnail_url,
                    'DRS_ID' : drs_id,
                    'HasManifest' : False if drs_id == "" else True
                }

                constituent_type = self.constituenttypes.get(int(row['ConstituentTypeID']))
                if constituent_type not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems'][constituent_type] = []
                self.records[row['RecID']]['RelatedItems'][constituent_type].append(constituent_dict)

                # KEEPS RELATED SITES SORTED: POTENTIAL RESOURCE DRAIN
                self.records[row['RecID']]['RelatedItems'][constituent_type].sort(key=itemgetter('DisplayText'))

                res.append(f'Published-{row["RecID"]}')
            except:
                err.append(f'Published-{row["RecID"]}')

        return { 'published_worker_constituents' : { 'res' : res, 'err' : err } }
