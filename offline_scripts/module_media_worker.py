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

        thumbnails = []

        for row in new_rows:
            row = self.sanitize(row)

            row['MediaType'] = self.mediatypes.get(row['MediaTypeID'])
            if 'RenditionNumber' in row:
                row['Number'] = row['RenditionNumber'] 
                number = row['Number']
                row['ID'] = row['RenditionNumber']
                
                row['AllNumbers'] = list(set([number, number[number.find('_')+1:], "".join(number.split()), "".join(number.split('_'))]))
            
            if 'MediaView' in row and 'PublicCaption' in row:
                subjects = ": ".join([row['MediaView'], row['PublicCaption']])
                row['Subjects'] = subjects
                row['DisplayText'] = subjects
            
            if 'DateOfCapture' in row: 
                row['Date'] = row['DateOfCapture']
            
            row['Roles'] = []

            if 'Department' in row:
                row['Credit'] = row['Department']

            row['PrimaryDisplay'] = {}

            if 'ArchIDNum' in row:
                row['PrimaryDisplay']['DRS_ID'] = row['ArchIDNum']
                thumbnail_url = self.thumbnail_url(row['ArchIDNum'])
            else:
                if 'ThumbPathName' in row and 'ThumbFileName' in row:
                    thumbnail_url = self.get_media_url(row['ThumbPathName'], row['ThumbFileName'])

            if 'MediaTypeID' in row: 
                thumbnail_id = f'{self.mediatypes.get(row["MediaTypeID"])}-{row["RecID"]}'  # NOT USED?

            if len(thumbnail_url) and thumbnail_id not in self.thumbnail_urls:
                self.thumbnail_urls[thumbnail_id] = { 'Thumbnail_ID' : thumbnail_id, 'url' : thumbnail_url }

            row['PrimaryDisplay']['MediaMasterID'] = row['RecID']
            row['PrimaryDisplay']['Thumbnail'] = thumbnail_url
            if 'MainPathName' in row and 'MainFileName' in row:
                row['PrimaryDisplay']['Main'] = self.get_media_url(row['MainPathName'], row['MainFileName'])

            row['ES_index'] = '3dmodels' if '3d' in row['MediaType'].lower() else row['MediaType'].lower()

            self.records[row["RecID"]] = row

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

            return self.records, self.relations, self.thumbnail_urls, { 'media_worker_res' : res, 'media_worker_err' : err }