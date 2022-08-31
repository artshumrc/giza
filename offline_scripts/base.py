try:
    from os import cpu_count
    from typing import Iterable
    from concurrent.futures import ThreadPoolExecutor
    from classifications import CLASSIFICATIONS, CONSTITUENTTYPES, MEDIATYPES
    from helper_date_conversion import Date_Conversion
    from cursor_FSS import file_open
except ImportError as error:
    print(error)

drs_metadata = {}

class Base:
    """
    Super class for all Workers.

    Methods
    -------
    - sanitize (dict) -> dict : cleans up a row before further processing
    - get_media_url (str, str) -> str : constructs and returns the url to a file on the media server
    - thumbnail_url (str) -> str : constructs and returns the url to a thumbnail
    - add_to_display ()

    - media
    - sites
    - objects
    - published
    - photographers
    - constituents
    
    NOTE: Media include maps, diary pages, photos etc.
    

    - build_media() -> Media_Worker : builds the basic object JSON record
    - start() -> dict, dict : the start method of the Media_Worker module
    """
    """ The Base class provides variables and methods shared to all workers classes (each module). 
    NOTE: 

    """

    def __init__(self, module_type=None):
        self.module_type = module_type

        self.dc = Date_Conversion(module_type)

        self.constituenttypes = CONSTITUENTTYPES
        self.classifications = CLASSIFICATIONS
        self.mediatypes = MEDIATYPES

        self.thumbnail_urls = {}

        self.records = {}
        self.relations = {}
        self.futures = []
        self.counter = 0

    def sanitize(self, row:dict) -> dict:
        try:
            row = { k : '' if v == ",," else v for k, v in row.items() }                                        # REMOVE DOUBLE COMMAS
            row = { k : 'null' if v == "" else v for k, v in row.items() }                                      # EMPTY VALUES TO NULL
            row = { k : v for k, v in row.items() if not (type(v) == str and v.lower() == 'null') }             # REMOVE ALL NULL VALUES
            row = { k : v.replace('  ', '') if type(v) == str and '  ' in v else v for k, v in row.items() }    # REMOVE DOUBLE SPACES
            row = { k : v.rstrip() if type(v) == str else v for k, v in row.items() }                           # REMOVE RIGHT WHITE SPACES
            row = { k : int(v) if (type(v) != int and v.isdigit()) else v for k, v in row.items() }             # NON-DIGITS TO DIGITS
        except Exception as e:
            print(f'Could not sanitize row: {e}')
        finally:
            return row

    def get_media_url(self, path:str, filename:str) -> str:
        if 'nrs.harvard.edu' in path: return f'{path}/{filename}'
        idx = path.find('images')
        if idx == -1:
            idx = path.find('documents')
            if idx == -1: return ""
        if filename.endswith('bmp'): return ""
        path = path[idx:].replace('\\','/')
        if not path.endswith('/'): path = path + '/'
        return f'https://gizamedia.rc.fas.harvard.edu/{path}{filename}'

    def thumbnail_url(self, id:str) -> str:
        return f'https://ids.lib.harvard.edu/ids/iiif/{id}/full/200,/0/default.jpg'

    # def add_to_display(self, row:dict, data:Iterable) -> dict:
    #     """
    #     Adds a piece of data to the display property of the row being processed. 
    #     This property is rendered on the website in search-result-details.html

    #     Parameters
    #     ----------
    #     - row (dict) : row that is being processed
    #     - data (iterable) : data that is added to the display property. This should be an iterable, a list of dicts or a single dict.

    #     Returns
    #     -------
    #     - row (dict) : the row that is being processed
    #     """
    #     # return row
    #     if not 'Display' in row: row['Display'] = {}
    #     if type(data) == list: 
    #         for item in data:
    #             if type(item) == str:
    #                 row['Display'][item] = row[item]
    #     # if type(data) == dict:
    #         # if not 'Display' in row: row['Display'] = {}
    #         # for key, value in data.items():
    #             # row['Display'][key] = value
    #     return row

    def media(self, doc_type:str, rows:list):
        """
        Completes the media record with various bits and pieces of information, 
        including on manifests, display images and related items. The method deploys 
        multiple instances of Worker, a sub-class of Base (see this file), to update
        the records efficiently.

        NOTE: RecID is not MediaMasterID: for the Sites module this is the SiteID.

        Parameters
        ----------
        - rows (list) : a list of dictionaries with data to be applied to the class' records variable

        Returns
        -------
        - dict : processing results
        """

        from module import overall_progress
                
        res, err = [], []

        sorted_by_mmid = {}

        for row in rows:
            if row['RecID'] not in sorted_by_mmid: sorted_by_mmid[row['RecID']] = []
            sorted_by_mmid[row['RecID']].append(row)

        def progress_indicator(future):
            try:
                """ This local method processes the response from each individual process """
                result = future.result()
                if len(result.res):
                    res.append(result.rec['RecID'])
                    self.records[result.rec['RecID']].update(result.rec)
                    self.thumbnail_urls.update(result.thumbnail_urls)
                else:
                    err.append(result.rec['RecID'])
                self.counter = self.counter + 1
            except Exception as e:
                print(e)

        manifests = overall_progress['iiif']['compilation'] if len(overall_progress['iiif']['compilation']) else file_open('compiled', 'iiif', 'iiif', True)
        met = overall_progress['met']['compilation'] if len(overall_progress['met']['compilation']) else file_open('compiled', 'relations', 'met', True)

        # TO PREVENT RACE CONDITIONS EACH INDIVIDUAL RECORD IS UPDATED IN ITS OWN THREAD
        with ThreadPoolExecutor(int((cpu_count()/2)-1)) as executor:
        # with ThreadPoolExecutor(1) as executor:
            for row in sorted_by_mmid.values():
                future = executor.submit(Worker, self.records[row[0]['RecID']], doc_type, row, manifests, met)
                future.add_done_callback(progress_indicator)

        # file_save('compiled', 'iiif', manifests)

        return { f'{self.module_type}_worker_media' : { 'res' : res, 'err' : err } }

    def sites(self, rows:list):
        """
        Updates and adds sites to the RelatedItems property. These records are kept in self.records on the class.

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
                row = self.sanitize(row)

                if 'RelatedItems' not in self.records[row['RecID']]: self.records[row['RecID']]['RelatedItems'] = {}
                if 'Sites' not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems']['Sites'] = []
                
                if 'ArchIDNum' in row:
                    thumbnail_url = self.thumbnail_url(row['ArchIDNum'])
                    if len(thumbnail_url) and row['ArchIDNum'] not in self.thumbnail_urls:
                        self.thumbnail_urls[row['ArchIDNum']] = { 
                            'Thumbnail_ID' : row['ArchIDNum'], 
                            'url' : thumbnail_url
                        }
                else:
                    if 'ThumbPathName' in row and 'ThumbFileName' in row:
                        thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])

                site = {
                    'RecID' : row['SiteID'],
                    'SiteName' : row['SiteName'],
                    'SiteNumber' : row['SiteNumber'],
                    'DisplayText' : f'{row["SiteName"]}, {row["SiteNumber"]}',
                    'Thumbnail' : thumbnail_url if len(thumbnail_url) else "thumbnails/no_image.jpg",
                    'Thumbnail_ID' : row['ArchIDNum'],
                    'DRS_ID' : row['ArchIDNum'],
                    'HasManifest' : False if row['ArchIDNum'] == "" else True
                }
                
                self.records[row['RecID']]['RelatedItems']['Sites'].append(site)

                # UNPUBLISHED DOCUMENTS ARE GIVEN SITES FOR THE "MENTIONED ON THIS PAGE" SECTION
                if 'ClassificationID' in row and CLASSIFICATIONS[row['ClassificationID']] == "UnpublishedDocuments":
                    if 'Mentioned' not in self.records[row['RecID']]: self.records[row['RecID']]['Mentioned'] = {}
                    if 'Sites' not in self.records[row['RecID']]['Mentioned']: self.records[row['RecID']]['Mentioned']['Sites'] = []
                    self.records[row['RecID']]['Mentioned']['Sites'].append(site)

                # KEEPS RELATED OBJECTS SORTED: POTENTIAL RESOURCE DRAIN
                # self.records[row['RecID']]['Relateditems']['Sites'].sort(key=operator.itemgetter('DisplayText'))

                res.append(f'{self.module_type}-{row["RecID"]}')
            except:
                err.append(f'{self.module_type}-{row["RecID"]}')

        return { f'{self.module_type}_worker_sites' : { 'res' : res, 'err' : err } }
    
    def objects(self, rows:list):
        """
        Updates and adds objects to the RelatedItems property. These records are kept in self.records on the class.

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

                row = self.sanitize(row)

                if 'RelatedItems' not in self.records[row['RecID']]: self.records[row['RecID']]['RelatedItems'] = {}
               
                classification = CLASSIFICATIONS[row['ClassificationID']]
                if classification not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems'][classification] = []

                if 'Title' not in row: 
                    if classification == "DiaryPages":
                        idx = row['ObjectNumber'].find('_')
                        row['Title'] = row['ObjectNumber'][idx+1:]
                    else:
                        row['Title'] = "[No Title]"
                
                if 'ArchIDNum' in row:
                    thumbnail_url = self.thumbnail_url(row['ArchIDNum'])
                    if len(thumbnail_url) and row['ArchIDNum'] not in self.thumbnail_urls:
                        self.thumbnail_urls[row['ArchIDNum']] = { 
                            'Thumbnail_ID' : row['ArchIDNum'], 
                            'url' : thumbnail_url 
                        }
                else:
                    if 'ThumbPathName' in row and 'ThumbFileName' in row:
                        thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])

                self.records[row['RecID']]['RelatedItems'][classification].append({
                    'RecID': row['ObjectID'],
                    'Title': row['Title'],
                    'DisplayText': row['Title'],
                    'ClassificationID': row['ClassificationID'],
                    'Number': row['ObjectNumber'],
                    'Date': "" if row['ObjectDate'].lower() == "null" else row['ObjectDate'],
                    'Thumbnail' : thumbnail_url if len(thumbnail_url) else "thumbnails/no_image.jpg",
                    'Thumbnail_ID' : row['ArchIDNum'],
                    'DRS_ID' : row['ArchIDNum'],
                    # 'HasManifest': False if row['ArchIDNum'] == "" else True
                })
                
                # KEEPS RELATED OBJECTS SORTED: POTENTIAL RESOURCE DRAIN
                # self.records[row['RecID']]['Relateditems'][classification].sort(key=operator.itemgetter('DisplayText'))

                res.append(f'{CLASSIFICATIONS[row["ClassificationID"]]}-{row["RecID"]}')
            except:
                err.append(f'{CLASSIFICATIONS[row["ClassificationID"]]}-{row["RecID"]}')

        return { f'{self.module_type}_worker_objects' : { 'res' : res, 'err' : err } }

    def published(self, rows:list):
        """
        Updates and adds PublishedDocuments to the RelatedItems property. These records are kept in self.records on the class.

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
                row = self.sanitize(row)

                if 'RelatedItems' not in self.records[row['RecID']]: self.records[row['RecID']]['RelatedItems'] = {}
                if 'PublishedDocuments' not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems']['PublishedDocuments'] = []

                # NOTE: Some dates like '1990-91' will cause an index error in ElasticSearch, because 
                # dynamic mapping tries to assign a date-field to what is essentially a string. 

                # TODO: Add a new method to the Date_Conversion class to deal with the above types of dates
                
                document = {
                    'RecID' : row['ReferenceID'],
                    'BoilerText' : row['BoilerText'],
                    'DisplayText' : row['BoilerText'],
                    'PublicationDate' : Date_Conversion('published').chkDatePattern(row['DisplayDate']),
                    'URL' : self.get_media_url(row['MainPathName'], row['MainFileName'])
                }

                if 'ThumbPathName' and 'ThumbFileName' in row:
                    thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])

                    thumbnail_id = f'PublishedDocuments-{row["ReferenceID"]}'

                    if len(thumbnail_url) and thumbnail_id not in self.thumbnail_urls:
                        self.thumbnail_urls[thumbnail_id] = { 'Thumbnail_ID' : thumbnail_id, 'url' : thumbnail_url }
                        document['Thumbnail'] = thumbnail_url

                    # self.thumbnail_urls.append({ 'Thumbnail_ID' : f'PublishedDocuments-{row["ReferenceID"]}', 'url' : document['Thumbnail'] })

                self.records[row['RecID']]['RelatedItems']['PublishedDocuments'].append(document)

                # KEEPS RELATED SITES SORTED: POTENTIAL RESOURCE DRAIN
                # self.records[row['RecID']]['Relateditems']['PublishedDocuments'].sort(key=operator.itemgetter('DisplayText'))

                res.append(f'{self.module_type}-{row["RecID"]}')
            except:
                err.append(f'{self.module_type}-{row["RecID"]}')

        return { f'{self.module_type}_worker_published' : { 'res' : res, 'err' : err } }

    def photographers(self, rows:list):
        """
        Updates and adds photographers to the manifests. RecID is the MediaMasterID from TMS.

        NOTE: RecID is the MediaMasterID in TMS

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
                row = self.sanitize(row)

                manifest_id = f'{MEDIATYPES[row["MediaTypeID"]]}-{row["RecID"]}'

                if 'Role' in row:
                    if 'DisplayName' in row: 
                        if 'DisplayDate' in row:
                            self.relations[manifest_id]['manifest']['metadata'].append({ 'Label' : row['Role'], 'Value' : f'{row["DisplayName"]}, {row["DisplayDate"]}' })
                        else:
                            self.relations[manifest_id]['manifest']['metadata'].append({ 'Label' : row['Role'], 'Value' : f'{row["DisplayName"]}' })

                res.append(manifest_id)
            except:
                err.append(manifest_id)

        return { f'{self.module_type}_worker_photographers' : { 'res' : res, 'err' : err } }

    def constituents(self, rows:list):
        """
        Updates and adds constituents to the RelatedItems property. These records are kept in self.records on the class.

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
                row = self.sanitize(row)
                
                if 'RelatedItems' not in self.records[row['RecID']]: self.records[row['RecID']]['RelatedItems'] = {}

                constituent_type = CONSTITUENTTYPES[row['ConstituentTypeID']]
                if constituent_type not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems'][constituent_type] = []

                if 'ArchIDNum' in row:
                    thumbnail_url = self.thumbnail_url(row['ArchIDNum'])
                    if len(thumbnail_url) and row['ArchIDNum'] not in self.thumbnail_urls:
                        self.thumbnail_urls[row['ArchIDNum']] = { 
                            'Thumbnail_ID' : row['ArchIDNum'], 
                            'url' : thumbnail_url 
                        }
                else:
                    if 'ThumbPathName' in row and 'ThumbFileName' in row:
                        thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])

                if 'Roles' not in self.records[row['RecID']]: self.records[row['RecID']]['Roles'] = []

                if row['Role'] not in self.records[row['RecID']]['Roles']:
                    if row['Role'] == "Photographer": 
                        self.records[row['RecID']]['Roles'].insert(0, row['Role'])
                    else: 
                        self.records[row['RecID']]['Roles'].append(row['Role'])

                # THIS SHOULD BE SPECIFIC TO THE SITES MODULE
                if 'Tomb Owner' in row['Role']: 
                    self.records[row['RecID']]['TombOwner'] = row
                if constituent_type in ['ModernPeople', 'AncientPeople']:
                    if constituent_type not in self.records[row['RecID']]: self.records[row['RecID']][constituent_type] = []
                    self.records[row['RecID']][constituent_type].append(row['DisplayName'])

                relatedItem = {}

                if 'ConstituentID' in row: relatedItem['RecID'] = row['ConstituentID']
                if 'Role' in row: relatedItem['Role'] = row['Role']
                if 'RoleID' in row: relatedItem['RoleID'] = row['RoleID']
                if 'DisplayName' in row: 
                    relatedItem['DisplayName'] = row['DisplayName']
                    relatedItem['DisplayText'] = row['DisplayName']
                if 'DisplayDate' in row: relatedItem['DisplayDate'] = row['DisplayDate']
                if 'Remarks' in row: relatedItem['Description'] = row['Remarks']
                if len(thumbnail_url): relatedItem['Thumbnail'] = thumbnail_url
                if 'ArchIDNum' in row:
                    relatedItem['DRS_ID'] = row['ArchIDNum']
                    relatedItem['Thumbnail_ID'] = row['ArchIDNum']

                self.records[row['RecID']]['RelatedItems'][constituent_type].append(relatedItem)

                # KEEPS RELATED SITES SORTED: POTENTIAL RESOURCE DRAIN
                # self.records[row['RecID']]['Relateditems'][constituent_type].sort(key=operator.itemgetter('DisplayText'))

                res.append(f'{CONSTITUENTTYPES[row["ConstituentTypeID"]]}-{row["RecID"]}')
            except Exception as e:
                err.append(f'{CONSTITUENTTYPES[row["ConstituentTypeID"]]}-{row["RecID"]}')

        return { f'{self.module_type}_worker_constituents' : { 'res' : res, 'err' : err } }

class Worker(Base):
    """
    Sub-class of Base for heavy lifting to process RelatedItems and manifests. This class serves to update RelatedItems 
    shared across all records and update the manifests for each module when the media method is called. 
    This class takes a particular record and a set of associated records to extract data for manifests and updates 
    the Mirador base IIIF records passed in as a dictionary. The class runs two separate loops (the first to update
    RelatedItems and the second to generate manifests) to prevent size changes of the RelatedItems dict during the 
    manifest generation.

    Parameters
    ----------
    - rec (dict) : the record that is being updated
    - rec_type (str) : the category of record that is being updated
    - new_rows (list) : the records associated with this particular record
    - manifests (dict) : the manifests as assembled so far by the program
    - met (dict) : MET data constructed separately
    - drs_metadata (dict) : metadata acquired from DRS for updating the records and manifests
    """

    def __init__(self, rec:dict, doc_type:str, new_rows:list, manifests:dict=None, met:dict=None):
        super().__init__()

        from module_iiif_worker import check_drs
        from module_iiif_worker import new_manifest
        from module_iiif_worker import add_manifest

        global drs_metadata
        if not len(drs_metadata):
            drs_metadata = check_drs()

        self.rec = rec
        
        self.res = []
        self.err = []

        self.relations = {}

        try:
            
            # FIRST LOOP TO UPDATE RECORD
            for idx, row in enumerate(new_rows):
                row = self.sanitize(row)
                
                # ADD RELATED ITEMS
                if 'RelatedItems' not in rec: rec['RelatedItems'] = {}

                # ADD MEDIA TYPES IN RELATED ITEMS
                media_type = MEDIATYPES[row['MediaTypeID']]
                if media_type not in rec['RelatedItems']: rec['RelatedItems'][media_type] = []
                if media_type == 'Image': rec['HasPhoto'] = True
            
                if 'ArchIDNum' in row:
                    thumbnail_url = self.thumbnail_url(row['ArchIDNum'])
                else:
                    if 'ThumbPathName' in row and 'ThumbFileName' in row:
                        thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])

                if thumbnail_url is not None and ('ArchIDNum' in row and row['ArchIDNum'] not in self.thumbnail_urls):
                    self.thumbnail_urls[row['ArchIDNum']] = { 
                        'Thumbnail_ID' : row['ArchIDNum'], 
                        'url' : thumbnail_url 
                    }
                    
                if row['MediaTypeID'] == 3:
                    if not row['MainFileName'].endswith('mp4'):
                        continue

                if bool(row['PrimaryDisplay']):
                    rec['PrimaryDisplay'] = {}

                    if len(thumbnail_url): rec['PrimaryDisplay']['Thumbnail'] = thumbnail_url

                    if 'ArchIDNum' in row: 
                        rec['PrimaryDisplay']['Thumbnail_ID'] = row['ArchIDNum']
                        rec['PrimaryDisplay']['DRS_ID'] = row['ArchIDNum']
                    if 'MainPathName' in row and 'MainFileName' in row:
                        rec['PrimaryDisplay']['Main'] = self.get_media_url(row['MainPathName'], row['MainFileName'])
                    if 'MediaView' in row and 'PublicCaption' in row:
                        rec['PrimaryDisplay']['DisplayText'] = ": ".join([row['MediaView'], row['PublicCaption']])
                    if 'RenditionNumber' in row:
                        rec['PrimaryDisplay']['Number'] = row['RenditionNumber']
                    if 'Description' in row:
                        rec['PrimaryDisplay']['Description'] = row['Description']
                    if not 'MediaMasterID' in row:
                        rec['PrimaryDisplay']['MediaMasterID'] = row['RecID']
                    else:
                        rec['PrimaryDisplay']['MediaMasterID'] = row['MediaMasterID']

                if met and ('MediaMasterID' in row and row['MediaMasterID'] in met):
                    rec['MET'] = met[row['MediaMasterID']]

                classification = CLASSIFICATIONS[row['ClassificationID']] if 'ClassificationID' in row else doc_type.title()

                if not (classification == '3Dmodels' and media_type == '3Dmodels'):
                    relatedItem = {
                        'RecID': row['RecID']
                    }
                    if 'MediaView' in row and 'PublicCaption' in row: 
                        relatedItem['DisplayText'] = ": ".join([row['MediaView'], row['PublicCaption']])
                    if 'ArchIDNum' in row:
                        relatedItem['Thumbnail_ID'] = row['ArchIDNum']
                        relatedItem['DRS_ID'] = row['ArchIDNum']
                    if bool(row['PrimaryDisplay']):
                        relatedItem['PrimaryDisplay'] = bool(row['PrimaryDisplay'])
                    if len(thumbnail_url): relatedItem['Thumbnail'] = thumbnail_url
                    if 'MainPathName' in row and 'MainFileName' in row:
                        relatedItem['Main'] = self.get_media_url(row['MainPathName'], row['MainFileName'])
                    if 'RenditionNumber' in row: relatedItem['Number'] = row['RenditionNumber']
                    if 'Description' in row: relatedItem['Description'] = row['Description']

                    self.rec['RelatedItems'][media_type].append(relatedItem)

                self.rec = rec

            # SECOND LOOP TO GENERATE/UPDATE MANIFEST
            for idx, row in enumerate(new_rows):
                try:
                    row = self.sanitize(row)

                    rec_id = f'{doc_type.title()}-{row["RecID"]}'

                    # if 'MediaTypeID' in row: rec_id = f'{MEDIATYPES[row["MediaTypeID"]]}-{row["RecID"]}'
                    if 'ConstituentTypeID' in row: rec_id = f'{CONSTITUENTTYPES[row["ConstituentTypeID"]]}-{row["RecID"]}'
                    # else:
                        # rec_id = f'{doc_type.title()}-{row["RecID"]}'

                    # THIS RECORD HAS A DRS ID AND THAT DRS ID EXISTS WITH DRS
                    if 'ArchIDNum' in row and row['ArchIDNum'] in drs_metadata:

                        try:
                            if rec_id not in manifests:

                                # ADD A NEW MANIFEST
                                manifests[rec_id] = new_manifest(rec_id, row)

                            else:

                                # UPDATE EXISTING MANIFEST
                                manifests[rec_id] = add_manifest(rec, row, manifests[rec_id], idx)

                        except Exception as e:
                            self.err.append({ rec_id : idx })
                    
                    self.res.append({ rec_id : idx })
                except Exception as e:
                    self.err.append({ rec_id : idx })

        except Exception as e:
            self.err.append({ rec_id : idx })
            print(e)