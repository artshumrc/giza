try:
    from os import cpu_count
    from concurrent.futures import ThreadPoolExecutor, wait
    from operator import itemgetter
    from base import Base
except ImportError as error:
    print(error)

class Objects_Worker(Base):
    """
    Sub-class of Base for the 'objects' base setup. 
    
    NOTE: Objects include artifacts, but also unpublished diaries, plans, maps, object register pages etc.
    
    Methods
    -------
    - build_objects() -> Objects_Worker : builds the basic object JSON record
    - start() -> dict, dict : the start method of the Objects_Worker module
    - altnums(rows=list) -> dict : updates alternative numbers in the object records
    - geocodes(rows=list) -> dict : updates geocodes in the object records
    - flexfields(rows=list) -> dict : updates flexfields in the object records
    - unpublished(rows=list) -> dict : updates unpublished documents in the object's RelatedItems property
    """
    def __init__(self, rows, cols, data=None):
        super().__init__('objects')

        self.rows = rows
        self.cols = cols
        self.data = data

    def build_objects(self):
        """
        Transforms the top-level record to a JSON format.

        Parameters
        ----------
        None

        Returns
        -------
        - self (Objects_Worker) : the instance of the class used by Module to call the worker method on this instance Base class
        """

        try:

            # COMBINE ROWS AND COLS TO SINGLE DICTIONARY
            rows = [{ y : row[self.cols.index(y)] for y in self.cols } for row in self.rows]
            
            for row in rows:
                row = { k : int(v) if v.isdigit() else v for k, v in row.items() }                                  # NON-DIGITS TO DIGITS
                row = { k : v.replace(',,', '') if type(v) == str else v for k, v in row.items() }                  # REMOVE DOUBLE COMMAS
                row = { k : v.replace('  ', '') if type(v) == str else v for k, v in row.items() }                  # REMOVE DOUBLE SPACES
                row = { k : v.rstrip() if type(v) == str else v for k, v in row.items() }                           # REMOVE RIGHT WHITE SPACES
                
                # RECOGNIZE ENTRY-DATES IN TITLE IF DOCUMENT TYPE IS 'DiaryPages'
                # 1) WOULD THIS BE USEFUL FOR OTHER DOCUMENT TYPES?
                # 2) SHOULD WE TRY TO PARSE ALL FIELDS TO EXTRACT ANY OTHER POTENTIAL DATE RANGES?
                if 'DiaryPages' in self.classifications.get(int(row['ClassificationID'])).lower():
                    if 'Title' in row and (type(row['Title']) == str and '_' in row['Title']) or (row['Title'] == 'NULL'):
                        if row['Title'] != 'NULL':
                            row['EntryDate'] = row['Title']
                        else:
                            row['Title'] = row['EntryDate']
                if 'EntryDate' in row:
                    if type(row['EntryDate']) == str and row['EntryDate'].lower() != 'null':
                        date = self.dc.chkDatePattern(row['EntryDate'])
                        if date is not None:
                            row['EntryDate_string'] = date
                            row['EntryDate_ms'] = [float(x[1]) for x in row['EntryDate_string']]

                # ASSIGN MET TERMS
                row['MET'] = []
                
                number = row['Number']

                row['Classification'] = self.classifications.get(int(row['ClassificationID']))
                if row['Classification'] == "DiaryPages" and row['Title'] == None:
                    row['Title'] = number[number.find('_')+1:]

                row['DisplayText'] = row['Title']
                row['AllNumbers'] = list(set([number, row['Title'], "".join(number.split())]))
                row['Roles'] = []
                row['HasPhoto'] = False
                row['ES_index'] = self.classifications.get(int(row['ClassificationID'])).lower()

                if str(row['RecID']) in self.records and '_' in row['Title']: 
                    continue

                self.records[str(row['RecID'])] = row

            self.dc.save_progress()

            return self
        except Exception as e:
            print(e)

    def start(self):
        """
        The start method of the Objects_Worker module, relying on multithreading, calls the 
        following local and Base methods simultaneously:
        1) Sites (Base)
        2) Media (Base)
        3) Altnums (local)
        4) Geocodes (local)
        5) Published (Base)
        6) Flexfields (local)
        7) Unpublished (local)
        8) Constituents (Base)

        Returns
        -------
        - self.records (dict) : data relevant to generation of object records
        - self.relations (dict) : data relevant to manifest generation derived from the object records
        - self.thumbnail_urls (dict) : data relevant to thumbnail downloading
        - dict : processing results
        """
        with ThreadPoolExecutor(int((cpu_count()/2)-1)) as executor:
            for rows in self.data:

                # COMBINE ROWS AND COLS TO SINGLE DICTIONARY
                row = [{ y : row[rows['cols'].index(y)] for y in rows['cols'] } for row in rows['rows']]
                
                # OBJECTS TASKS
                if 'objects_sites' in rows['key']: self.futures.append(executor.submit(self.sites, row))
                if 'objects_media' in rows['key']: self.futures.append(executor.submit(self.media, row))
                if 'objects_altnums' in rows['key']: self.futures.append(executor.submit(self.altnums, row))
                if 'objects_geocodes' in rows['key']: self.futures.append(executor.submit(self.geocodes, row))
                if 'objects_published' in rows['key']: self.futures.append(executor.submit(self.published, row))
                if 'objects_flexfields' in rows['key']: self.futures.append(executor.submit(self.flexfields, row))
                if 'objects_unpublished' in rows['key']: self.futures.append(executor.submit(self.unpublished, row))
                if 'objects_constituents' in rows['key']: self.futures.append(executor.submit(self.constituents, row))

            done, not_done = wait(self.futures)
            
            res, err = {}, {}

            for future in done:
                result = future.result()
                method = list(result.keys())[0]
                res[method] = { 'res' : { 'summary' : len(result[method]['res']), 'res' : result[method]['res'] }}
                err[method] = { 'err' : { 'summary' : len(result[method]['err']), 'err' : result[method]['err'] }}

            return self.records, self.relations, self.thumbnail_urls, { 'objects_worker_res' : res, 'sites_worker_err' : err }

    def altnums(self, rows:list):
        """
        Updates alternative numbers in the object records. These records are kept in self.records on the class.

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
                if 'AlternativeNumbers' not in self.records[row['RecID']]: self.records[row['RecID']]['AlternativeNumbers'] = []

                altnum = row['AltNum']
                without_prefix = altnum[altnum.find('_')+1:]
                description = row['Description'] if row['Description'] != "NULL" else ""
                self.records[row['RecID']]['AlternativeNumbers'].append({"Description" : altnum, "Note" : description, 'without_prefix': without_prefix})
                self.records[row['RecID']]['AllNumbers'].extend((altnum, without_prefix))

                self.records[row['RecID']]['AllNumbers'] = list(set(self.records[row['RecID']]['AllNumbers']))
                self.records[row['RecID']]['AllNumbers'] = [x for x in self.records[row['RecID']]['AllNumbers'] if x is not None]

                res.append(f'Object-{row["RecID"]}')
            except:
                err.append(f'Object-{row["RecID"]}')
        
        return { 'objects_worker_altnums' : { 'res' : res, 'err' : err } }

    def geocodes(self, rows:list):
        """
        Updates geocodes in the object records. These records are kept in self.records on the class.

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
                self.records[row['RecID']]['Geocode'] = { 'GeoCodeID' : row['GeoCodeID'], 'Geocode' : row['GeoCode'], 'Region' : row['Region'], 'City' : row['City'] }

                res.append(f'Object-{row["RecID"]}')
            except:
                err.append(f'Object-{row["RecID"]}')
        
        return { 'objects_worker_geocodes' : { 'res' : res, 'err' : err } }

    def flexfields(self, rows:list):
        """
        Updates flexfields in the object records. These records are kept in self.records on the class.

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
                if 'FlexFields' not in self.records[row['RecID']]: self.records[row['RecID']]['FlexFields'] = {}
                if row['GroupName'] not in self.records[row['RecID']]['FlexFields']: self.records[row['RecID']]['FlexFields'][row['GroupName']] = []
                self.records[row['RecID']]['FlexFields'][row['GroupName']].append({row['UserFieldName'] : row['FieldValue']})
                
                res.append(f'Object-{row["RecID"]}')
            except:
                err.append(f'Object-{row["RecID"]}')
        
        return { 'objects_worker_flexfields' : { 'res' : res, 'err' : err } }

    def unpublished(self, rows:list):
        """
        Updates unpublished documents in the object's RelatedItems property. These records are kept in self.records on the class.

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
                if 'UnpublishedDocuments' not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems']['UnpublishedDocuments'] = []

                drs_id = row['ArchIDNum']

                if 'ConstituentTypeID' in row: 
                    thumbnail_id = f'{self.constituenttypes.get(int(row["ConstituentTypeID"]))}-{row["RecID"]}' # NOT USED?
                if 'ClassificationID' in row: 
                    thumbnail_id = f'{self.classifications.get(int(row["ClassificationID"]))}-{row["RecID"]}'
                if 'MediaTypeID' in row: 
                    thumbnail_id = f'{self.mediatypes.get(int(row["MediaTypeID"]))}-{row["RecID"]}'  # NOT USED?

                if drs_id:
                    thumbnail_url = self.thumbnail_url(drs_id)

                if drs_id.lower() == "null" or not drs_id:
                    thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])

                if len(thumbnail_url) and thumbnail_id not in self.thumbnail_urls:
                    self.thumbnail_urls[thumbnail_id] = { 'Thumbnail_ID' : thumbnail_id, 'url' : thumbnail_url }

                self.records[row['RecID']]['RelatedItems']['UnpublishedDocuments'].append({
                    'RecID' : row['UnpublishedID'],
                    'Text' : row['UnpublishedTitle'],
                    'DisplayText' : row['UnpublishedTitle'],
                    'Date' : "" if row['ObjectDate'].lower() == "null" else row['ObjectDate'],
                    'Number' : row['ObjectNumber'],
                    'Thumbnail' : thumbnail_url,
                    'Thumbnail_ID' : thumbnail_id,
                    'HasManifest' : False if drs_id == "" else True
                })

                self.records[row['RecID']]['relateditems']['unpubdocs'].sort(key=itemgetter('displaytext'))

                res.append(f'Object-{row["RecID"]}')
            except:
                err.append(f'Object-{row["RecID"]}')
        
        return { 'objects_worker_unpublished' : { 'res' : res, 'err' : err } }