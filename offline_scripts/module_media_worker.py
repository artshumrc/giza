try:
    from os import cpu_count
    from concurrent.futures import ThreadPoolExecutor, wait
    from base import Base
except ImportError as error:
    print(error)

class Media_Worker(Base):
    """
    Sub-class of Base for the 'media' base setup. 
    
    NOTE: Media include maps, diary pages, photos etc.
    
    Methods
    -------
    - build_media() -> Media_Worker : builds the basic object JSON record
    - start() -> dict, dict : the start method of the Media_Worker module
    """
    def __init__(self, rows, cols, data=None):
        super().__init__('media')
        
        self.rows = rows
        self.cols = cols
        self.data = data

    def build_media(self):
        """
        Transforms the top-level record to a JSON format.

        Parameters
        ----------
        None

        Returns
        -------
        - self (Media_Worker) : the instance of the class used by Module to call the worker method on this instance Base class
        """

        # CONVERT ROWS TO DICTS; MICROFILM AND DOCUMENT TYPES ARE FILTERED OUT BY SKIPPING INDICES 4 AND 5
        new_rows = [{ y : row[self.cols.index(y)] for y in self.cols } for row in self.rows if int(row[self.cols.index('MediaTypeID')]) not in [4, 5]]

        for row in new_rows:
            row = { k : '' if v == ",," else v for k, v in row.items() }                                        # REMOVE DOUBLE COMMAS
            row = { k : v.replace('  ', '') if type(v) == str and '  ' in v else v for k, v in row.items() }    # REMOVE DOUBLE SPACES
            row = { k : v.rstrip() if type(v) == str else v for k, v in row.items() }                           # REMOVE RIGHT WHITE SPACES

            media = {}
            media['RecID'] = row['RecID']
            media['MediaType'] = self.mediatypes.get(int(row['MediaTypeID']))
            media['Number'] = "" if row['RenditionNumber'].lower() == "null" else row['RenditionNumber']
            
            number = media['Number']
            media['AllNumbers'] = list(set([number, number[number.find('_')+1:], "".join(number.split()), "".join(number.split('_'))]))
            
            if row['Description'] is not None: media['Description'] = "" if row['Description'].lower() == "null" else row['Description']
            if row['PublicCaption'] is not None or row['MediaView'] is not None: 
                mediaview = "" if row['MediaView'].lower() == "null" else row['MediaView']
                caption = "" if row['PublicCaption'].lower() == "null" else row['PublicCaption']
                subjects = ": ".join([mediaview, caption])
                media['Mediaview'] = mediaview
                media['Subjects'] = subjects
                media['DisplayText'] = subjects
            
            if row['Remarks'] is not None: media['Remarks'] = "" if row['Remarks'].lower() == "null" else row['Remarks']
            if row['DateOfCapture'] is not None: media['Date'] = "" if row['DateOfCapture'].lower() == "null" else row['DateOfCapture']
            if row['Department'] is not None: media['Department'] = "" if row['Department'].lower() == "null" else row['Department']
            if row['ProblemsQuestions'] is not None: media['ProblemsQuestions'] = "" if row['ProblemsQuestions'].lower() == "null" else row['ProblemsQuestions']
            
            media['Roles'] = []

            drs_id = "" if str(row['ArchIDNum']).lower() == "null" else str(row['ArchIDNum'])

            thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])
            if not thumbnail_url and drs_id: thumbnail_url = self.thumbnail_url(drs_id)

            media['DRS_ID'] = drs_id
            media['PrimaryDisplay'] = {
                'MediaMasterID' : row['RecID'],
                'Thumbnail' : thumbnail_url,
                'Main' : self.get_media_url(row['MainPathName'], row['MainFileName']),
                'DRS_ID' : drs_id,
                'HasManifest' : False if drs_id == "" else True
            }

            media = { k : int(v) if type(v) is str and v.isdigit() else v for k, v in media.items() }  # NON-DIGITS TO DIGITS
            media = { k : None if v == "NULL" else v for k, v in media.items() }                       # NULL VALUES TO NONE
            media['ES_index'] = media['MediaType'].lower()

            self.records[str(row["RecID"])] = media

        return self

    def start(self):
        """
        The start method of the Published_Worker module, relying on multithreading, calls the 
        following local and Base methods simultaneously:
        1) Sites (Base)
        2) Objects (Base)
        3) Published (Base)
        4) Constituents (Base)
        5) Photographers (Base)

        Returns
        -------
        - self.records (dict) : data relevant to generation of media records
        - self.relations (dict) : data relevant to manifest generation derived from the published records
        - dict : processing results
        """
        with ThreadPoolExecutor(int((cpu_count()/2)-1)) as executor:
            for rows in self.data:

                # CONVERT ROWS TO DICTS; COL VALUES: RecID, MediaTypeID, Role, DisplayName, DisplayDate
                # PHOTO TYPES ARE FILTERED OUT BY EQUALING FOR MEDIATYPEID == 1
                row = [{ y : row[rows['cols'].index(y)] for y in rows['cols'] } for row in rows['rows'] if int(row[rows['cols'].index('MediaTypeID')]) == 1]
                
                # MEDIA TASKS
                if 'media_sites' in rows['key']: self.futures.append(executor.submit(self.sites, row))
                if 'media_objects' in rows['key']: self.futures.append(executor.submit(self.objects, row))
                if 'media_published' in rows['key']: self.futures.append(executor.submit(self.published, row))
                if 'media_constituents' in rows['key']: self.futures.append(executor.submit(self.constituents, row))
                if 'media_photographers' in rows['key']: self.futures.append(executor.submit(self.photographers, row))

            done, not_done = wait(self.futures)
            
            res, err = {}, {}

            for future in done:
                result = future.result()
                method = list(result.keys())[0]
                res[method] = { 'res' : { 'summary' : len(result[method]['res']), 'res' : result[method]['res'] }}
                err[method] = { 'err' : { 'summary' : len(result[method]['err']), 'err' : result[method]['err'] }}

            return self.records, self.relations, { 'media_worker_res' : res, 'media_worker_err' : err }