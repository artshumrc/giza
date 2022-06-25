try:
    from typing import Tuple, Union
    from base import Base
    from cursor_FSS import file_open
    from cursor_TMS import TMS
    from sql import DRS
except ImportError as error:
    print(error)

class IIIF_Worker(Base):
    """
    Sub-class of Base for the IIIF base setup
    
    Methods
    -------
    - build_iiif() -> IIIF_Worker : constructs a base manifest record for photo records
    - start() -> dict, dict : the start method of the iiif_worker module
    - check_drs(tms=TMS) -> list : fetches all ArchIDNums from TMS and constructs the urls required to download DRS data   
    """
    def __init__(self, rows:list, cols:list, data:list=None):
        super().__init__('iiif')
        
        self.rows = rows
        self.cols = cols
        self.data = data

        try:
            self.drs_metadata = file_open('tables', 'drs', 'iiif')
        except:
            raise "The IIIF module could not access DRS data from file"

    def build_iiif(self) -> Base:
        """
        Constructs a base manifest record for photo records

        Returns
        -------
        - self (IIIF_Worker) : the instance of the class used by Module to call the worker method on this instance Base class
        """

        try:
      
            # CONVERT ROWS TO DICTS
            # EXCLUDE NON-PHOTO RECORDS BY EQUALING MEDIATYPEID TO 1
            new_rows = [{ y : row[self.cols.index(y)] for y in self.cols } for row in self.rows if int(row[self.cols.index('MediaTypeID')]) == 1]
            
            def generate_iiif_manifest(data:dict) -> Union[dict,None]:
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
                    if data['DRS_ID'] in self.drs_metadata:
                        manifest = build_base_manifest(data['Manifest_ID'], data)
                        manifest["sequences"] = build_manifest_sequences(data['Manifest_ID'])
                        manifest["sequences"][0]["canvases"] = [build_manifest_canvas(data['Manifest_ID'], data['DRS_ID'], 0, data['resource'] if 'resource' in data else None, None, None)]
                        return manifest
                    else:
                        return None
                except Exception as e:
                    raise e

            def build_base_manifest(manifest_id:str, data:dict) -> dict:
                """
                Constructs the base for a IIIF manifest. Subsequent methods add to this method's result.

                Parameters
                ----------
                - manifest_id (str) : the identifier for the manifest
                - data (dict) : parameters for description and label

                Returns
                -------
                - ob (dict) : the base for a IIIF manifest
                """

                try:
                    ob = {
                        "description": data['description'],
                        "@context": "https://iiif.io/api/presentation/2/context.json",
                        "@id": manifest_id,
                        "label": data['label'],
                        "@type": "sc:Manifest"
                    }
                    
                    if 'metadata' in data: ob['metadata'] = data['metadata']
                    
                    return ob
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

            def build_manifest_canvas(manifest_id:str, drs_id:str, idx:int, resource:dict, label:str, metadata:list) -> dict:
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
                except Exception as e:
                    raise e

            def build_resource(drs_id) -> dict:
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
                        "width": self.drs_metadata[drs_id]['width'],
                        "@id": f'https://ids.lib.harvard.edu/ids/iiif/{drs_id}/full/full/0/default.jpg',
                        "@type": "dctypes:Image",
                        "height": self.drs_metadata[drs_id]['height'],
                        "service": {
                            "@context": "https://iiif.io/api/presentation/2/context.json",
                            "@id": f'https://ids.lib.harvard.edu/ids/iiif/{drs_id}',
                            "profile": "http://iiif.io/api/image/2/level1.json"
                        }
                    }
                
                except Exception as e:
                    raise e

            for row in new_rows:

                description = "" if row['Description'].lower() == "null" else row['Description']
                mediaview = "" if row['MediaView'].lower() == "null" else row['MediaView']
                caption = "" if row['PublicCaption'].lower() == "null" else row['PublicCaption']
                subjects = ": ".join([mediaview, caption])
                drs_id = "" if row['ArchIDNum'].lower() == "null" else row['ArchIDNum']
                number = "" if row['RenditionNumber'].lower() == "null" else row['RenditionNumber']
                department = "" if row['Department'].lower() == "null" else row['Department']
                date = "" if row['DateOfCapture'].lower() == "null" else row['DateOfCapture']
                problemsquestions = "" if row['ProblemsQuestions'].lower() == "null" else row['ProblemsQuestions']
                
                manifest_id = f'{self.mediatypes.get(int(row["MediaTypeID"]))}-{row["RecID"]}'
                # manifest_id = f'{"".join([x.title() for x in row["MediaView"].split(" ")])}-{row["RecID"]}'

                metadata = []
                if number: metadata.append({'label' : 'ID', 'value' : number})
                if department: metadata.append({'label' : 'Department', 'value' : department})
                if subjects: metadata.append({'label' : 'Subjects', 'value' : subjects})
                if date: metadata.append({'label' : 'Date', 'value' : date})
                if problemsquestions: metadata.append({'label' : 'Problems/Questions', 'value' : problemsquestions})
                if description == "": description = caption

                manifest_ob = {
                    "Manifest_ID": manifest_id,
                    "DRS_ID": drs_id,
                    "description": description,
                    "label": mediaview,
                    "metadata": metadata
                }

                # CHECK TO UPDATE EXISTING MANIFESTS FIRST
                if manifest_id in self.relations and self.relations[manifest_id]['manifest'] is not None:
                    resource = self.relations[manifest_id]['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']
                    if drs_id in resource['@id']:
                        manifest_ob['resource'] = resource

                # ADD THE NEW MANIFEST TO THE MANIFEST DICTIONARY ON THE CLASS OBJECT
                self.relations[manifest_id] = { 
                    # "id": manifest_id,
                    "RecID" : manifest_id,
                    "ES_index" : self.mediatypes.get(int(row["MediaTypeID"])),
                    "manifest": generate_iiif_manifest(manifest_ob), "ES_index" : "iiif"
                }

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

def check_drs(tms:TMS) -> Union[list, dict]:
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
        # RETURNING PROPER DRS_METADATA FOUND ON DISK
        drs_metadata = file_open('tables', 'drs', 'iiif')
        if drs_metadata:
            return drs_metadata
        else:
            try:
                
                # DOWNLOAD DRS DATA FROM GIZACARDTMS
                ArchIDNums = tms.fetch(DRS.pop(), 'DRS')
                return [{ 'id' : row[0], 'url' : f'https://ids.lib.harvard.edu/ids/iiif/{row[0]}/info.json' } for row in ArchIDNums[0] if row[0].lower() != 'null']
            except:
                raise
    except Exception as e:
        raise e