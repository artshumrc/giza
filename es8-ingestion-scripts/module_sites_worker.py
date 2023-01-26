from os import cpu_count
from concurrent.futures import ThreadPoolExecutor, wait
from re import sub
from base import Base

class Sites_Worker(Base):
    """
    Sub-class of Base for the 'sites' base setup
    
    Methods
    -------
    - build_sites () -> Sites_Worker : builds the basic site JSON record
    - start () -> dict, dict : the start method of the Sites_Worker module
    - dates (rows) -> dict : the result of the operation
    - altnums (rows) -> dict : the result of the operation
    """
    def __init__(self, rows, cols, data=None):
        super().__init__('sites')

        self.rows = rows
        self.cols = cols
        self.data = data

    def build_sites(self):
        """
        Transforms the top-level record to a JSON format.

        NOTE: RecID is the Site ID in TMS

        Parameters
        ----------
        None

        Returns
        -------
        - self (Sites_Worker) : the instance of the class used by Module to call the worker method on this instance Base class
        """

        # COMBINE ROWS AND COLS TO SINGLE DICTIONARY
        new_rows = [{ y : row[self.cols.index(y)] for y in self.cols } for row in self.rows ]

        for row in new_rows:
            row = self.sanitize(row)

            row = { k : sub(r"(\w)([A-Z])", r"\1 \2", v) if type(v) == str else v for k, v in row.items() }     # INSERT SPACES BEFORE CAPITAL LETTERS MID-SENTENCE

            row['DisplayText'] = row['Number']

            row['AllNumbers'] = list(set([row['Number'], row['Number'][row['Number'].find('_')+1:], "".join(row['Number'].split())]))
            
            row['Roles'], row['People'], row['DateValues'] = [], [], []

            row['ES_index'] = self.module_type.lower()
            
            self.records[row['RecID']] = row
        
        return self

    def start(self):
        """
        The start method of the Sites_Worker module, relying on multithreading, calls the 
        following local and Base methods simultaneously:
        1) Dates (local)
        2) Media (Base)
        3) Altnums (local)
        4) Objects (Base)
        5) Published (Base)
        6) Constituents (Base)

        Returns
        -------
        - self.records (dict) : data relevant to generation of site records
        - self.relations (dict) : data relevant to manifest generation derived from the site records
        - dict : processing results
        """

        with ThreadPoolExecutor(int((cpu_count()/2)-1)) as executor:
            for rows in self.data:

                # COMBINE ROWS AND COLS TO SINGLE DICTIONARY
                new_rows = [{ y : int(row[rows['cols'].index(y)]) if row[rows['cols'].index(y)].isdigit() else row[rows['cols'].index(y)] for y in rows['cols'] } for row in rows['rows']]
                
                # SITES TASKS
                if 'sites_dates' in rows['key']: self.futures.append(executor.submit(self.dates, new_rows))
                if 'sites_media' in rows['key']: self.futures.append(executor.submit(self.media, 'sites', new_rows))
                if 'sites_altnums' in rows['key']: self.futures.append(executor.submit(self.altnums, new_rows))
                if 'sites_objects' in rows['key']: self.futures.append(executor.submit(self.objects, new_rows))
                if 'sites_published' in rows['key']: self.futures.append(executor.submit(self.published, new_rows))
                if 'sites_constituents' in rows['key']: self.futures.append(executor.submit(self.constituents, new_rows))

            done, not_done = wait(self.futures)
            
            res, err = {}, {}

            for future in done:
                result = future.result()
                method = list(result.keys())[0]
                res[method] = { 'res' : { 'summary' : len(result[method]['res']), 'res' : result[method]['res'] }}
                err[method] = { 'err' : { 'summary' : len(result[method]['err']), 'err' : result[method]['err'] }}

            return self.records, self.relations, self.thumbnail_urls, { 'sites_worker_res' : res, 'sites_worker_err' : err }

    def dates(self, rows:list):
        """
        Updates date values in the site records, kept in self.records on this class instance. 
        
        NOTE: RecID is the Site ID in TMS

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

                if 'EventType' in row and 'DateText' in row:

                    if 'SiteDates' not in self.records[row['RecID']]: self.records[row['RecID']]['SiteDates'] = []
                    self.records[row['RecID']]['SiteDates'].append({ 'Type': row['EventType'], 'Date': row['DateText'] })
                    self.records[row['RecID']]['DateValues'].append(row['DateText'])
                                    
                    res.append(row['RecID'])
            except:
                err.append(row['RecID'])
        return { 'sites_worker_dates' : { 'res' : res, 'err' : err } }

    def altnums(self, rows:list):
        """
        Updates alternative numbers in the site records, kept in self.records on this class instance.

        NOTE: RecID is the Site ID in TMS

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

                if 'AlternativeNumbers' not in self.records[row['RecID']]: self.records[row['RecID']]['AlternativeNumbers'] = []
                if 'AlternativeNumbersTypes' not in self.records[row['RecID']]: self.records[row['RecID']]['AlternativeNumbersTypes'] = []
                self.records[row['RecID']]['AlternativeNumbers'].append({ "Description" : row['AltNum'], "Note" : row['Description'] })

                res.append(row['RecID'])
            except:
                err.append(row['RecID'])

        return { 'sites_worker_altnums' : { 'res' : res, 'err' : err } }
