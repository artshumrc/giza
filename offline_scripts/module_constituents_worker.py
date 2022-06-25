try:
    from os import cpu_count
    from concurrent.futures import ThreadPoolExecutor, wait
    from base import Base
    from re import sub
except ImportError as error:
    print(error)

class Constituents_Worker(Base):
    """
    Sub-class of Base for the 'constituents' base setup. 
    
    NOTE: Constituents include ancient and modern people, institutions etc.
    
    Methods
    -------
    - build_constituents() -> Constituents_Worker : builds the basic object JSON record
    - start() -> dict, dict : the start method of the Constituents_Worker module
    - altnames(rows=list) -> dict : updates AlternativeNames in the constituent records
    """
    def __init__(self, rows, cols, data=None):
        super().__init__('constituents')
        
        self.rows = rows
        self.cols = cols
        self.data = data

    def build_constituents(self):
        """
        Transforms the top-level record to a JSON format.

        Parameters
        ----------
        None

        Returns
        -------
        - self (Constituents_Worker) : the instance of the class used by Module to call the worker method on this instance Base class
        """

        # CONVERT ROWS TO DICTS; COL VALUES: RecID, Number
        new_rows = [{ y : row[self.cols.index(y)] for y in self.cols } for row in self.rows ]

        for row in new_rows:
            row = { k : int(v) if v.isdigit() else v for k, v in row.items() }                                  # NON-DIGITS TO DIGITS
            row = { k : None if v == "NULL" else v for k, v in row.items() }                                    # NULL VALUES TO NONE
            row = { k : '' if v == ",," else v for k, v in row.items() }                                        # REMOVE DOUBLE COMMAS
            row = { k : v.replace('  ', '') if type(v) == str and '  ' in v else v for k, v in row.items() }    # REMOVE DOUBLE SPACES
            row = { k : v.rstrip() if type(v) == str else v for k, v in row.items() }                           # REMOVE RIGHT WHITE SPACES
            row = { k : sub(r"(\w)([A-Z])", r"\1 \2", v) if type(v) == str else v for k, v in row.items() }     # INSERT SPACES BEFORE CAPITAL LETTERS MID-SENTENCE
            row = { k : None if ('BeginDate' in k or 'EndDate' in k) and v == 0 else v for k, v in row.items() }

            if ('BeginDate' in row and row['BeginDate'] is not None) or ('EndDate' in row and row['EndDate'] is not None):
                row['EntryDate'] = "-".join([str(row['BeginDate']), str(row['EndDate'])])
            if 'EntryDate' in row:
                if type(row['EntryDate']) == str and row['EntryDate'].lower() != 'null':
                    date = self.dc.chkDatePattern(row['EntryDate'])
                    if date is not None:
                        row['EntryDate_string'] = date
                        row['EntryDate_ms'] = [float(x[1]) for x in row['EntryDate_string']]

            row['Type'] = self.constituenttypes.get(int(row['ConstituentTypeID']))
            row['DisplayText'] = row['DisplayName']
            row['ES_index'] = self.constituenttypes.get(int(row['ConstituentTypeID'])).lower()

            self.records[str(row['RecID'])] = row
        
        return self

    def start(self):
        """
        The start method of the Constituents_Worker module, relying on multithreading, calls the 
        following local and Base methods simultaneously:
        1) Sites (Base)
        2) Media (Base)
        3) Objects (Base)
        4) Altnames (local)
        5) Published (Base)

        Returns
        -------
        - self.records (dict) : data relevant to generation of object records
        - self.relations (dict) : data relevant to manifest generation derived from the constituent records
        - dict : processing results
        """
        with ThreadPoolExecutor(int((cpu_count()/2)-1)) as executor:
            for rows in self.data:

                # CONVERT ROWS TO DICTS
                row = [{ y : row[rows['cols'].index(y)] for y in rows['cols'] } for row in rows['rows']]

                # CONSTITUENTS TASKS
                if 'constituents_sites' in rows['key']: self.futures.append(executor.submit(self.sites, row))
                if 'constituents_media' in rows['key']: self.futures.append(executor.submit(self.media, row))
                if 'constituents_objects' in rows['key']: self.futures.append(executor.submit(self.objects, row))
                if 'constituents_altnames' in rows['key']: self.futures.append(executor.submit(self.altnames, row))
                if 'constituents_published' in rows['key']: self.futures.append(executor.submit(self.published, row))

            done, not_done = wait(self.futures)
            
            res, err = {}, {}

            for future in done:
                result = future.result()
                method = list(result.keys())[0]
                res[method] = { 'res' : { 'summary' : len(result[method]['res']), 'res' : result[method]['res'] }}
                err[method] = { 'err' : { 'summary' : len(result[method]['err']), 'err' : result[method]['err'] }}

            return self.records, self.relations, self.thumbnail_urls, { 'constituents_worker_res' : res, 'constituents_worker_err' : err }

    def altnames(self, rows:list):
        """
        Updates AlternativeNames in the constituent records. These records are kept in self.records on the class.

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
                if 'AlternativeNames' not in self.records[row['RecID']]: self.records[row['RecID']]['AlternativeNames'] = []
                self.records[row['RecID']]['AlternativeNames'].append({ 'Name' : row['DisplayName'], 'Type' : row['NameType'] })

                res.append(f'Constituent-{row["RecID"]}')
            except:
                err.append(f'Constituent-{row["RecID"]}')

        return { 'constituents_worker_altnames' : { 'res' : res, 'err' : err } }