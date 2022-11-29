try:
    from typing import Tuple, Union
    from base import Base
    from cursor_FSS import file_open
    from cursor_TMS import TMS
    from sql import DRS
except ImportError as error:
    print(error)

drs_metadata = {}

class IIIF_Worker(Base):
    """
    Sub-class of Base for the IIIF base setup
    
    Methods
    -------
    - build_iiif() -> IIIF_Worker : constructs a base manifest record for photo records
    - start() -> dict, dict : the start method of the iiif_worker module
    - check_drs(tms=TMS) -> list : fetches all ArchIDNums from TMS and constructs the urls required to download DRS data   
    """
    def __init__(self, rows:list=None, cols:list=None, data:list=None):
        super().__init__('iiif')
        
        self.rows = rows
        self.cols = cols
        self.data = data

        # try:
        #     self.drs_metadata = check_drs()
        # except:
        #     raise "The IIIF module could not access DRS data from file"

    def build_iiif(self) -> Base:
        """
        Constructs a base manifest record for photo records.

        NOTE: RecID is the MediaMasterID in TMS

        Returns
        -------
        - self (IIIF_Worker) : the instance of the class used by Module to call the worker method on this instance Base class
        """

        try:
      
            # CONVERT ROWS TO DICTS
            # EXCLUDE NON-PHOTO RECORDS BY EQUALING MEDIATYPEID TO 1
            # new_rows = [{ y : row[self.cols.index(y)] for y in self.cols } for row in self.rows if int(row[self.cols.index('MediaTypeID')]) == 1]

            new_rows = [{ y : row[self.cols.index(y)] for y in self.cols } for row in self.rows ]

            for row in new_rows:

                row = self.sanitize(row)

                manifest_id = f'{self.mediatypes.get(row["MediaTypeID"])}-{row["RecID"]}'

                # ADD THE NEW MANIFEST TO THE MANIFEST DICTIONARY ON THE CLASS OBJECT
                self.relations[manifest_id] = new_manifest(manifest_id, row)

            return self

        except Exception as e:
            print(e)
            raise e

    def start(self) -> Tuple[dict, dict]:
        """
        The start method of the IIIF_Worker module.
        1) calls the super class photographers method.

        Returns
        -------
        - self.relations (dict) : data relevant to manifest generation derived from the downloaded records
        - dict : processing results
        """
        # CONVERT ROWS TO DICTS (ONLY PHOTO RECORDS)
        rows = [{ y : row[self.data[0]['cols'].index(y)] for y in self.data[0]['cols'] } for row in self.data[0]['rows'] if int(row[self.data[0]['cols'].index('MediaTypeID')]) == 1]

        photographers = self.photographers(rows)
        
        photographers_result = {}
        
        photographers_result['iiif_worker_photographers'] = { 
            'res' : { 
                'summary' : len(photographers['iiif_worker_photographers']['res']),
                'res' : photographers['iiif_worker_photographers']['res']
            },
            'err' : {
                'summary' : len(photographers['iiif_worker_photographers']['err']),
                'err' : photographers['iiif_worker_photographers']['err']
            }
        }

        return self.records, self.relations, self.thumbnail_urls, { 'iiif_worker_res' : photographers_result }

def check_drs(tms:TMS=None) -> Union[list, dict]:
    """
    Fetches all ArchIDNums from TMS and constructs the urls required to download DRS data.

    Parameters
    ----------
    - tms (TMS) : a configured TMS instance

    Returns
    -------
    - dict : dictionary with the drs metadata
    #### OR
    - list : list of dictionaries with ArchIDNums and corresponding urls linked to DRS to generate drs metadata from
    """
    try:
        # RETURNING DRS_METADATA FOUND ON DISK
        global drs_metadata
        
        if not len(drs_metadata): drs_metadata = file_open('tables', 'drs', 'iiif')
        
        if len(drs_metadata):
            if any([x for x in list(drs_metadata.keys()) if type(x) == str]):
                drs_metadata = { int(k) : v for k, v in drs_metadata.items() }
            return drs_metadata
        else:
            try:

                # ATTEMPT TO DOWNLOAD DRS DATA FROM GIZACARDTMS
                if tms is not None:
                    ArchIDNums = tms.fetch(DRS.pop(), 'DRS')
                    return [{ 'id' : row[0], 'url' : f'https://ids.lib.harvard.edu/ids/iiif/{row[0]}/info.json' } for row in ArchIDNums[0] if row[0].lower() != 'null']
                else:
                    return {}
            except:
                raise
    except Exception as e:
        raise e

def new_manifest(manifest_id, row):
    return { 
        "RecID" : manifest_id,
        "manifest": build_manifest(manifest_id, row),
        "ES_index" : "iiif"
    }

def build_manifest(manifest_id:str, rec:dict) -> dict:
    manifest, metadata = {}, []

    metadata = add_metadata(rec)

    if 'MediaView' in manifest and 'PublicCaption' in manifest:
        subjects = ": ".join([manifest['MediaView'], manifest['PublicCaption']])
        metadata.append({'label' : 'Subjects', 'value' : subjects})
        manifest['label'] = subjects                

    if 'ArchIDNum' in rec: manifest['DRS_ID'] = rec['ArchIDNum']
    if 'Description' in rec: 
        manifest['description'] = rec['Description']
    else:
        if 'PublicCaption' in rec: 
            manifest['Description'] = rec['PublicCaption']

    manifest['metadata'] = metadata

    return generate_iiif_manifest(manifest_id, manifest)

def generate_iiif_manifest(manifest_id:str, rec:dict) -> Union[dict, None]:
    """
    Compiles a JSON representation of a IIIF manifest

    Parameters
    ----------
    - data (dict) : 

    Returns
    -------
    - manifest (dict) : the start of a IIIF manifest
    #### OR
    - None
    """

    try:
        if drs_exists(rec['DRS_ID']):
            
            manifest = build_base_manifest(manifest_id, rec)
            manifest["sequences"] = build_manifest_sequences(manifest_id)
            manifest["sequences"][0]["canvases"] = [
                build_manifest_canvas(
                    manifest_id, 
                    rec['DRS_ID'], 
                    0, 
                    manifest['resource'] if 'resource' in manifest else None, 
                    rec['Description'] if 'Description' in rec else None,
                    manifest['metadata'] if 'metadata' in manifest else None
                )
            ]

            return manifest
        else:
            return None
    except Exception as e:
        raise e

def drs_exists(drs_id):
    return True if drs_id in drs_metadata else False

def build_base_manifest(manifest_id:str, manifest:dict) -> dict:
    """
    Constructs the base for a IIIF manifest. Subsequent methods add to this method's result.

    Parameters
    ----------
    - manifest_id (str) : the identifier for the manifest
    - manifest (dict) : parameters for description and label

    Returns
    -------
    - ob (dict) : the base for a IIIF manifest
    """

    try:
        base_manifest = {
            "@context": "https://iiif.io/api/presentation/2/context.json",
            "@id": manifest_id,
            "@type": "sc:Manifest"
        }

        if 'description' in manifest: base_manifest['description'] = manifest['description']
        if 'label' in manifest: base_manifest['label'] = manifest['label']
        if 'metadata' in manifest: base_manifest['metadata'] = manifest['metadata']
        
        return base_manifest
    except Exception as e:
        raise e

def build_manifest_sequences(manifest_id:str) -> list:
    """
    Constructs a sequence list for a IIIF manifest

    Parameters
    ----------
    - manifest_id (str) : the identifier for the manifest

    Returns
    -------
    - list : a sequence list
    """

    try:
        return [
            {
                "label": "Default order",
                "@type": "sc:Sequence",
                "@id": manifest_id
            }
        ]
    except Exception as e:
        raise e

def build_manifest_canvas(manifest_id:str, drs_id:int, idx:int, resource:dict, label:str, metadata:list) -> dict:
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

    try:
        resource = build_resource(drs_id)

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
    except Exception as e:
        raise e

def build_resource(drs_id:int) -> dict:
    """
    Builds a manifest for the provided drs_id

    Parameters
    ----------
    - drs_id (str) : the identifier in drs

    Returns
    -------
    - dict : manifest resource
    """
    
    try:
    
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
    
    except Exception as e:
        raise e

def add_manifest(rec, row, manifest, idx):
    try:
        if 'Description' in row:
            description = row['Description']
        elif 'PublicCaption' in row:
            description = row['PublicCaption']
        elif 'MediaView' in row:
            description = row['MediaView']
        else:
            description = "[No title]"


        manifest['manifest']['sequences'][0]['canvases'].append(
            build_manifest_canvas(
                manifest['RecID'], 
                row['ArchIDNum'], 
                idx, 
                manifest['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource'], 
                description, 
                add_metadata(rec)
            )
        )

        if bool(row['PrimaryDisplay']):
            if str(row['ArchIDNum']) in manifest['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']["@id"]:
                manifest['manifest']['sequences'][0]['startCanvas'] = manifest['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']["@id"]

        return manifest
    except Exception as e:
        raise e

def add_metadata(rec:dict):
    """
    Adds metadata to manifest based on available data in record

    Parameters
    ----------
    - rec (dict) : dictionary of record that provides data to draw from

    Returns
    -------
    - metadata (list) : metadata to be added to the manifest
    """

    metadata = []

    # CAST LONG/INT TO STR TO PREVENT ES MAPPER INDEX ERROR LATER ON
    rec = { k : str(v) if type(v) == int else v for k, v in rec.items() }

    if 'RecID' in rec and rec['RecID']: metadata.append({ 'Label' : 'RecID', 'Value' : rec['RecID' ]})
    if 'SiteType' in rec and 'SiteType' in rec['SiteType']: metadata.append({ 'Label' : 'Site Type', 'Value' : rec['SiteType']['SiteType'] })
    if 'RenditionNumber' in rec: metadata.append({'label' : 'Rendition number', 'value' : rec['RenditionNumber'] })
    if 'Shafts' in rec and rec['Shafts']: metadata.append({ 'Label' : 'Shafts', 'Value' : rec['Shafts'] })
    if 'Number' in rec and rec['Number']: metadata.append({ 'Label' : 'Number', 'Value' : rec['Number'] })
    if 'Department' in rec and rec['Department']: metadata.append({ 'Label' : 'Department', 'Value' : rec['Department'] })
    if 'ClassificationText' in rec and rec['ClassificationText']: metadata.append({ 'Label' : 'Classification', 'Value' : rec['ClassificationText'] })
    if 'Provenance' in rec and rec['Provenance']: metadata.append({ 'Label' : 'Findspot', 'Value' : rec['Provenance'] })
    if 'Medium' in rec and rec['Medium']: metadata.append({ 'Label' : 'Material', 'Value' : rec['Medium'] })
    if 'Dimensions' in rec and rec['Dimensions']: metadata.append({ 'Label' : 'Dimensions', 'Value' : rec['Dimensions'] })
    if 'Creditline' in rec and rec['CreditLine']: metadata.append({ 'Label' : 'Credit Line', 'Value' : rec['CreditLine'] })
    if 'Notes' in rec and rec['Notes']: metadata.append({ 'Label' : 'Notes', 'Value' : rec['Notes'] })
    if 'ProblemsQuestions' in rec and rec['ProblemsQuestions']: metadata.append({ 'Label' : 'Problems/Questions', 'Value' : rec['ProblemsQuestions'] })
    if 'Subjects' in rec and rec['Subjects']: metadata.append({ 'Label' : 'Subjects', 'Value' : rec['Subjects'] })
    if 'ObjectOwnerDetails' in rec and rec['ObjectOwnerDetails']: metadata.append({ 'Label' : 'Object Ownership Information', 'Value' : rec['ObjectOwnerDetails'] })
    if 'ConstituentType' in rec and rec['ConstituentType']: metadata.append({ 'Label' : 'Type', 'Value' : rec['ConstituentType'] })
    if 'Gender' in rec and rec['Gender']: metadata.append({ 'Label' : 'Gender', 'Value' : rec['Gender'] })
    if 'Institution' in rec and rec['Institution']: metadata.append({ 'Label' : 'Institution', 'Value' : rec['Institution'] })
    if 'Remarks' in rec and rec['Remarks']: metadata.append({ 'Label' : 'Remarks', 'Value' : rec['Remarks'] })
    if 'Roles' in rec and rec['Roles']: metadata = assign_roles(rec)
    if 'DateOfCapture' in rec: metadata.append({'label' : 'Date', 'value' : rec['DateOfCapture'] })
    if 'Date' in rec and rec['Date']: metadata.append({ 'Label' : 'Date', 'Value' : rec['Date'] })
    if 'DisplayDate' in rec and rec['DisplayDate']: metadata.append({ 'Label' : 'Nationality and Dates', 'Value' : rec['DisplayDate'] })
    if 'EntryDate' in rec and rec['EntryDate']: metadata.append({ 'Label' : 'Date of Register Entry', 'Value' : rec['EntryDate'] })
    if 'Period' in rec and rec['Period']: metadata.append({ 'Label' : 'Period', 'Value' : rec['Period'] })
    if 'SiteDates' in rec and rec['SiteDates']:
        dates = []
        for sitedate in rec['SiteDates']:
            dates.append(sitedate['Date'])
        metadata.append({ 'Label' : sitedate['Type'], 'Value' : dates })
    if 'AlternativeNames' in rec and rec['AlternativeNames']: 
        names = []
        for name in rec['AlternativeNames']:
            names.append(f'{name["Type"]}: {name["Name"]}')
        metadata.append({'Label' : 'Also known as', 'Value' : names })
    if 'AlternativeNumbers' in rec:
        numbers = []
        note = ''
        for number in rec['AlternativeNumbers']:
            numbers.append(number['Description'])
            note = number["Note"]
        metadata.append({'Label' : note, 'Value' : numbers })

    return metadata

def assign_roles(rec:dict):
    """
    Adds roles of individuals (e.g. Excavator, Photographer etc.)

    Parameters
    ----------
    - rec (dict) : the dictionary that provides values to draw from

    Returns
    -------
    - metadata (list) : metadata to be added to the record
    """
    roles = []
    for role in rec['Roles']:
        value = []
        for category in rec['RelatedItems']:
            for item in rec['RelatedItems'][category]:
                if 'Role' in item and item['Role'] == role:
                    value.append(f'{item["DisplayText"]}, {item["DisplayDate"]}' if 'DisplayDate' in item else item['DisplayText'])
        roles.append({ 'Label' : role, 'Value' : value })
    return roles