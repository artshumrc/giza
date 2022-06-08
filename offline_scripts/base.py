try:
    from os import cpu_count
    from cursor_FSS import file_open
    from concurrent.futures import ThreadPoolExecutor
    from helper_date_conversion import ED
    from classifications import CLASSIFICATIONS, CONSTITUENTTYPES, MEDIATYPES
except ImportError as error:
    print(error)

class Base:
    """
    Super class for all Workers.

    Methods
    -------
    - get_media_url(path=, filename=) -> str : constructs and returns the url to a file on the media server
    - thumbnail_url(id=str) -> str : constructs and returns the url to a thumbnail

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

        self.ed = ED(module_type)

        self.constituenttypes = CONSTITUENTTYPES
        self.classifications = CLASSIFICATIONS
        self.mediatypes = MEDIATYPES

        self.records = {}
        self.relations = {}
        self.futures = []
        self.counter = 0

    def get_media_url(self, path:str, filename:str):
        if 'nrs.harvard.edu' in path: return f'{path}/{filename}'
        idx = path.find('images')
        if idx == -1:
            idx = path.find('documents')
            if idx == -1: return ""
        if filename.endswith('bmp'): return ""
        path = path[idx:].replace('\\','/')
        if not path.endswith('/'): path = path + '/'
        return f'https://gizamedia.rc.fas.harvard.edu/{path}{filename}'

    def thumbnail_url(self, id:str):
        return f'https://ids.lib.harvard.edu/ids/iiif/{id}/full/200,/0/default.jpg'

    def media(self, rows:list):
        """
        Completes the media record with various bits and pieces of information, 
        including on manifests, display images and related items. The method deploys 
        multiple instances of Worker, a sub-class of Base (see this file), to update
        the records efficiently.

        Parameters
        ----------
        - rows (list) : a list of dictionaries with data to be applied to the class' records variable

        Returns
        -------
        - dict : processing results
        """

        from module import overall_progress

        res, err = [], []

        sorted_by_row = {}

        for row in rows:
            if row['RecID'] not in sorted_by_row: sorted_by_row[row['RecID']] = []
            sorted_by_row[row['RecID']].append(row)

        def progress_indicator(future):
            try:
                """ This local method processes the response from each individual process """
                result = future.result()
                if len(result.res):
                    res.append(result.rec['RecID'])
                    self.records[str(result.rec['RecID'])].update(result.rec)
                    if len(result.relations):
                        self.relations[list(result.relations.keys())[0]] = list(result.relations.values())[0]
                else:
                    err.append(result.rec['RecID'])
                self.counter = self.counter + 1
            except Exception as e:
                print(e)

        manifests = overall_progress['iiif']['compilation'] if len(overall_progress['iiif']['compilation']) else file_open('compiled', 'iiif', 'iiif', True)
        met = overall_progress['met']['compilation'] if len(overall_progress['met']['compilation']) else file_open('compiled', 'relations', 'met', True)

        # TO PREVENT RACE CONDITIONS EACH INDIVIDUAL RECORD IS UPDATED IN A SEPARATE THREAD
        with ThreadPoolExecutor(int((cpu_count()/2)-1)) as executor:
            for row in sorted_by_row.values():
                if 'ConstituentTypeID' in row[0] and row[0]['ConstituentTypeID'].lower() != "null": doc_type = self.constituenttypes.get(int(row[0]['ConstituentTypeID']))
                if 'ClassificationID' in row[0] and row[0]['ClassificationID'].lower() != "null": doc_type = self.classifications.get(int(row[0]['ClassificationID']))
                if 'MediaTypeID' in row[0] and row[0]['MediaTypeID'].lower() != "null": doc_type = self.mediatypes.get(int(row[0]['MediaTypeID']))                    
                future = executor.submit(Worker, self.records[row[0]['RecID']], doc_type, row, manifests, met)
                future.add_done_callback(progress_indicator)

        # file_save('compiled', 'relations', self.relations, self.module_type)

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
                if 'RelatedItems' not in self.records[row['RecID']]: self.records[row['RecID']]['RelatedItems'] = {}
                if 'Sites' not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems']['Sites'] = []
                
                drs_id = "" if row['ArchIDNum'].lower() == "null" else row['ArchIDNum']
                thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])
                if not thumbnail_url and drs_id: thumbnail_url = self.thumbnail_url(drs_id)

                site = {
                    'RecID' : row['SiteID'],
                    'SiteName' : row['SiteName'],
                    'SiteNumber' : row['SiteNumber'],
                    'DisplayText' : f'{row["SiteName"]}, {row["SiteNumber"]}',
                    'Thumbnail' : thumbnail_url,
                    'HasManifest' : False if drs_id == "" else True
                }
                
                self.records[row['RecID']]['RelatedItems']['Sites'].append(site)

                # UNPUBLISHED DOCUMENTS ARE GIVEN SITES FOR THE "MENTIONED ON THIS PAGE" SECTION
                if 'ClassificationID' in row and self.classifications.get(int(row['ClassificationID'])) == "UnpublishedDocuments":
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
                if 'RelatedItems' not in self.records[row['RecID']]: self.records[row['RecID']]['RelatedItems'] = {}

                object_title = row['Title']
                if object_title.lower() == "null": object_title = "[No Title]"

                classification = self.classifications.get(int(row['ClassificationID']))
                if classification not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems'][classification] = []
                if classification == "DiaryPages" and row['Title'].lower() == "null":
                    idx = row['ObjectNumber'].find('_')
                    object_title = row['ObjectNumber'][idx+1:]

                drs_id = "" if row['ArchIDNum'].lower() == "null" else row['ArchIDNum']
                thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])
                if not thumbnail_url and drs_id: thumbnail_url = self.thumbnail_url(drs_id)              
                
                self.records[row['RecID']]['RelatedItems'][classification].append({
                    'RecID': row['ObjectID'],
                    'Title': row['Title'],
                    'DisplayText': row['Title'],
                    'ClassificationID': int(row['ClassificationID']),
                    'Number': row['ObjectNumber'],
                    'Date': "" if row['ObjectDate'].lower() == "null" else row['ObjectDate'],
                    'Thumbnail': thumbnail_url,
                    'HasManifest': False if drs_id == "" else True
                })
                
                # KEEPS RELATED OBJECTS SORTED: POTENTIAL RESOURCE DRAIN
                # self.records[row['RecID']]['Relateditems'][classification].sort(key=operator.itemgetter('DisplayText'))

                res.append(f'{self.classifications.get(int(row["ClassificationID"]))}-{row["RecID"]}')
            except:
                err.append(f'{self.classifications.get(int(row["ClassificationID"]))}-{row["RecID"]}')

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
                if 'RelatedItems' not in self.records[row['RecID']]: self.records[row['RecID']]['RelatedItems'] = {}
                if 'PublishedDocuments' not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems']['PublishedDocuments'] = []

                document = {
                    'RecID' : row['ReferenceID'],
                    'BoilerText' : row['BoilerText'],
                    'DisplayText' : row['BoilerText'],
                    # 'PublicationDate' : row['DisplayDate'],
                    'PublicationDate' : ED().extract_year(row['DisplayDate']),
                    'URL' : self.get_media_url(row['MainPathName'], row['MainFileName'])
                }

                if 'ThumbPathName' and 'ThumbFileName' in row:
                    document['Thumbnail'] = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])

                self.records[row['RecID']]['RelatedItems']['PublishedDocuments'].append(document)

                # KEEPS RELATED SITES SORTED: POTENTIAL RESOURCE DRAIN
                # self.records[row['RecID']]['Relateditems']['PublishedDocuments'].sort(key=operator.itemgetter('DisplayText'))

                res.append(f'{self.module_type}-{row["RecID"]}')
            except:
                err.append(f'{self.module_type}-{row["RecID"]}')

        return { f'{self.module_type}_worker_published' : { 'res' : res, 'err' : err } }

    def photographers(self, rows:list):
        """
        Updates and adds photographers to the manifests.

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
                manifest_id = f'{self.mediatypes.get(int(row["MediaTypeID"]))}-{row["RecID"]}'               
                
                self.relations[manifest_id]['manifest']['metadata'].append({
                    'Label' : "" if row['Role'].lower() == "null" else row['Role'], 
                    'Value' : f'{"" if row["DisplayName"].lower() == "null" else row["DisplayName"]}, {"" if row["DisplayDate"].lower() == "null" else row["DisplayDate"]}' if ("" if row["DisplayDate"].lower() == "null" else row["DisplayDate"]) else "" if row["DisplayName"].lower() == "null" else row["DisplayName"]
                })

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
                if 'RelatedItems' not in self.records[row['RecID']]: self.records[row['RecID']]['RelatedItems'] = {}

                constituent_type = self.constituenttypes.get(int(row['ConstituentTypeID']))
                if constituent_type not in self.records[row['RecID']]['RelatedItems']: self.records[row['RecID']]['RelatedItems'][constituent_type] = []

                drs_id = "" if row['ArchIDNum'].lower() == "null" else row['ArchIDNum']
                thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])
                if not thumbnail_url and drs_id: thumbnail_url = self.thumbnail_url(drs_id)
                
                if row['Role'] not in self.records[row['RecID']]['Roles']: 
                    if row['Role'] == "Photographer": 
                        self.records[row['RecID']]['Roles'].insert(0, row['Role'])
                    else: 
                        self.records[row['RecID']]['Roles'].append(row['Role'])

                # THIS SHOULD BE SPECIFIC TO THE SITES MODULE
                if row['Role'] == 'Tomb Owner': self.records[row['RecID']]['TombOwner'] = True
                if constituent_type in ['ModernPeople', 'AncientPeople']:
                    if constituent_type not in self.records[row['RecID']]: self.records[row['RecID']][constituent_type] = []
                    self.records[row['RecID']][constituent_type].append(row['DisplayName'])

                self.records[row['RecID']]['RelatedItems'][constituent_type].append({
                    'Role':  row['Role'],
                    'RoleID' : "" if not 'RoleID' in row else row['RoleID'],
                    'RecID' : row['ConstituentID'],
                    'DisplayName' : row['DisplayName'],
                    'DisplayDate' : row['DisplayDate'] if row['DisplayDate'] != "NULL" else "",
                    'DisplayText' : row['DisplayName'],
                    'Description' : row['Remarks'] if row['Remarks'] != "NULL" else "",
                    'Thumbnail' : thumbnail_url,
                    'HasManifest' : False if drs_id == "" else True
                })

                # KEEPS RELATED SITES SORTED: POTENTIAL RESOURCE DRAIN
                # self.records[row['RecID']]['Relateditems'][constituent_type].sort(key=operator.itemgetter('DisplayText'))

                res.append(f'{self.constituenttypes.get(int(row["ConstituentTypeID"]))}-{row["RecID"]}')
            except:
                err.append(f'{self.constituenttypes.get(int(row["ConstituentTypeID"]))}-{row["RecID"]}')

        return { f'{self.module_type}_worker_constituents' : { 'res' : res, 'err' : err } }

class Worker(Base):
    """
    Sub-class of Base for heavy lifting. This class only serves to update general 
    properties broadly shared across all records.
    """
    def __init__(self, rec, rec_type, new_rows, manifests=None, met=None):
        super().__init__()
      
        self.rec = rec
        self.rec_type = rec_type
        
        self.res = []
        self.err = []

        self.relations = {}

        try:

            for row in new_rows:
                try:
                    # ADD RELATED ITEMS
                    if 'RelatedItems' not in self.rec: self.rec['RelatedItems'] = {}

                    # ADD MEDIA TYPES IN RELATED ITEMS
                    media_type = self.mediatypes.get(int(row['MediaTypeID']))
                    if media_type not in self.rec['RelatedItems']: self.rec['RelatedItems'][media_type] = []
                    if media_type == 'Photos': self.rec['HasPhoto'] = True

                    # PREPARE DISPLAY TEXT
                    mediaview = "" if row['MediaView'].lower() == "null" else row['MediaView']
                    caption = "" if row['PublicCaption'].lower() == "null" else row['PublicCaption']
                    display_text = ": ".join([mediaview, caption])

                    # HAS A MANIFEST
                    drs_id = "" if row['ArchIDNum'].lower() == "null" else row['ArchIDNum']
                    has_manifest = False if drs_id == "" else True
                    
                    # CREATE THUMBNAIL
                    thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])
                    if not thumbnail_url and drs_id: thumbnail_url = self.thumbnail_url(drs_id)

                    if int(row['MediaTypeID']) == 3:
                        if not row['MainFileName'].endswith('mp4'):
                            continue

                    if bool(int(row['PrimaryDisplay'])):
                        self.rec['PrimaryDisplay'] = {
                            'Thumbnail' : thumbnail_url,
                            'Main' : self.get_media_url(row['MainPathName'], row['MainFileName']),
                            'DisplayText' : display_text,
                            'Number' : "" if row['RenditionNumber'].lower() == "null" else row['RenditionNumber'],
                            'Description' : "" if row['Description'].lower() == "null" else row['Description'],
                            'HasManifest' : has_manifest,
                            'MediaMasterID' : row['MediaMasterID']
                        }

                    if met and row['MediaMasterID'] in met:
                        self.rec['MET'] = met[row['MediaMasterID']]

                    classification = self.classifications.get(int(row['ClassificationID'])) if 'ClassificationID' in row and row['ClassificationID'].lower() != 'null' else rec_type.title()

                    if not (classification == '3Dmodels' and media_type == '3Dmodels'):
                        self.rec['RelatedItems'][media_type].append({
                            'MediaMasterID': row['MediaMasterID'],
                            'DisplayText': display_text,
                            'PrimaryDisplay': bool(int(row['PrimaryDisplay'])),
                            'Thumbnail': thumbnail_url,
                            'Main': self.get_media_url(row['MainPathName'], row['MainFileName']),
                            'Number': "" if row['RenditionNumber'].lower() == "null" else row['RenditionNumber'],
                            'Description': "" if row['Description'].lower() == "null" else row['Description'],
                            'HasManifest': has_manifest,
                            'DRS_ID': drs_id
                        })

                    if has_manifest:
                        try:
                            resource = manifests[f'{media_type}-{row["MediaMasterID"]}']['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']
                            canvas_label = manifests[f'{media_type}-{row["MediaMasterID"]}']['manifest']['description']
                            canvas_metadata = manifests[f'{media_type}-{row["MediaMasterID"]}']['manifest']['metadata']

                            rec_id = f'{classification}-{row["RecID"]}'
                        
                            if row['RecID'] not in self.relations.keys(): 
                                metadata = self.add_metadata(rec)
                                self.relations[rec_id] = {
                                    'Description': row['Description'],
                                    'Label': self.rec['DisplayText'],
                                    'Resources': [resource],
                                    'Classification': classification,
                                    'DRS_IDs' : [drs_id],
                                    'Canvas_labels' : [canvas_label],
                                    'Canvas_metadatas' : [canvas_metadata],
                                    'Metadata' : metadata
                                }
                            else:
                                self.relations[rec_id]['Resources'].append(resource)
                                self.relations[rec_id]['DRS_IDs'].append(drs_id)
                                self.relations[rec_id]['Canvas_labels'].append(canvas_label)
                                self.relations[rec_id]['Canvas_metadatas'].append(canvas_metadata)
                            if bool(int(row['PrimaryDisplay'])):
                                self.relations[rec_id]['startCanvas'] = drs_id

                        except Exception as e:
                            self.err.append(row['MediaMasterID'])
                    
                    self.res.append(row['MediaMasterID'])
                except Exception as e:
                    self.err.append(row['MediaMasterID'])

        except Exception as e:
            print(e)

    def add_metadata(self, rec:dict):
        """
        Adds specific metadata, based on what module the call originated from.

        Parameters
        ----------
        - rec (dict) : the dictionary that provides values to draw from

        Returns
        -------
        - metadata (list) : metadata to be added to the record
        """
        metadata = []

        # IF RECORD TYPE IS A SITE
        if self.rec_type == 'site':
            metadata = assign_roles(rec, metadata)

            if 'SiteType' in rec and 'SiteType' in rec['SiteType']: metadata.append({ 'Label' : 'Site Type', 'Value' : rec['SiteType']['SiteType'] })
            if 'Shafts' in rec and rec['Shafts']: metadata.append({ 'Label' : 'Shafts', 'Value' : rec['Shafts'] })
            if 'Remarks' in rec and rec['Remarks']: metadata.append({ 'Label' : 'Remarks', 'Value' : rec['Remarks'] })
            if 'ProblemsQuestions' in rec and rec['ProblemsQuestions']: metadata.append({ 'Label' : 'Problems/Questions', 'Value' : rec['ProblemsQuestions'] })
            if 'AlternativeNumbers' in rec and rec['AlternativeNumbers']: metadata.append({ 'Label' : 'Alternative Numbers', 'Value' : rec['AlternativeNumbers'] })
            if 'SiteDates' in rec and rec['SiteDates']:
                for sitedate in rec['SiteDates']:
                    metadata.append({ 'Label' : sitedate['Type'], 'Value' : sitedate['Date'] })
        
        # IF RECORD TYPE IS AN OBJECT
        if self.rec_type == 'object':
            metadata = assign_roles(rec, metadata)

            if 'Number' in rec and rec['Number']: metadata.append({ 'Label' : 'RecID', 'Value' : rec['Number'] })
            if 'Department' in rec and rec['Department']: metadata.append({ 'Label' : 'Department', 'Value' : rec['Department'] })
            if 'ClassificationText' in rec and rec['ClassificationText']: metadata.append({ 'Label' : 'Classification', 'Value' : rec['ClassificationText'] })
            if 'Provenance' in rec and rec['Provenance']: metadata.append({ 'Label' : 'Findspot', 'Value' : rec['Provenance'] })
            if 'Medium' in rec and rec['Medium']: metadata.append({ 'Label' : 'Material', 'Value' : rec['Medium'] })
            if 'Dimensions' in rec and rec['Dimensions']: metadata.append({ 'Label' : 'Dimensions', 'Value' : rec['Dimensions'] })
            if 'Creditline' in rec and rec['CreditLine']: metadata.append({ 'Label' : 'Credit Line', 'Value' : rec['CreditLine'] })
            if 'Notes' in rec and rec['Notes']: metadata.append({ 'Label' : 'Notes', 'Value' : rec['Notes'] })
            if 'Remarks' in rec and rec['Remarks']: metadata.append({ 'Label' : 'Remarks', 'Value' : rec['Remarks'] })
            if 'ProblemsQuestions' in rec and rec['ProblemsQuestions']: metadata.append({ 'Label' : 'Problems/Questions', 'Value' : rec['ProblemsQuestions'] })
            if 'Subjects' in rec and rec['Subjects']: metadata.append({ 'Label' : 'Subjects', 'Value' : rec['Subjects'] })
            if 'Date' in rec and rec['Date']: metadata.append({ 'Label' : 'Date', 'Value' : rec['Date'] })
            if 'EntryDate' in rec and rec['EntryDate']: metadata.append({ 'Label' : 'Date', 'Value' : rec['EntryDate'] })
            if 'ObjectOwnerDetails' in rec and rec['ObjectOwnerDetails']: metadata.append({ 'Label' : 'Object Ownership Information', 'Value' : rec['ObjectOwnerDetails'] })
            if 'Period' in rec and rec['Period']: metadata.append({ 'Label' : 'Period', 'Value' : rec['Period'] })
            if 'EntryDate' in rec and rec['EntryDate']: metadata.append({ 'Label' : 'Date of Register Entry', 'Value' : rec['EntryDate'] })
            if 'AlternativeNumbers' in rec: 
                [metadata.append({'Label' : altnum['Note'], 'Value' : altnum['Description'] }) for altnum in rec['AlternativeNumbers']]

        # IF RECORD TYPE IS AN OBJECT
        if self.rec_type == 'constituent':
            if 'ConstituentType' in rec and rec['ConstituentType']: metadata.append({ 'Label' : 'Type', 'Value' : rec['ConstituentType'] })
            if 'Gender' in rec and rec['Gender']: metadata.append({ 'Label' : 'Gender', 'Value' : rec['Gender'] })
            if 'Institution' in rec and rec['Institution']: metadata.append({ 'Label' : 'Institution', 'Value' : rec['Institution'] })
            if 'DisplayDate' in rec and rec['DisplayDate']: metadata.append({ 'Label' : 'Nationality and Dates', 'Value' : rec['DisplayDate'] })
            if 'Remarks' in rec and rec['Remarks']: metadata.append({ 'Label' : 'Remarks', 'Value' : rec['Remarks'] })
            if 'AlternativeNames' in rec and rec['AlternativeNames']: metadata.append({ 'Label' : 'Also Known As', 'Value' : [f"{altname['Type']}:{altname['Name']}" for altname in rec['AlternativeNames']] })
        
        return metadata

def assign_roles(rec:dict, metadata:list):
    """
    Adds specific metadata, based on what module the call originated from, specifically roles of individuals

    Parameters
    ----------
    - rec (dict) : the dictionary that provides values to draw from
    - metadata (list) : the metadata to add to

    Returns
    -------
    - metadata (list) : metadata to be added to the record
    """
    for role in rec['Roles']:
        value = []
        for category in rec['RelatedItems']:
            for item in rec['RelatedItems'][category]:
                if 'Role' in item and item['Role'] == role:
                    value.append(f'{item["DisplayText"]}, {item["DisplayDate"]}' if item['DisplayDate'] else item['DisplayText'])
        metadata.append({ 'Label' : role, 'Value' : value })
    return metadata