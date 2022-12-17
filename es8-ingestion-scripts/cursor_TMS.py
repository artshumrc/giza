from attr import Attribute


try:
    import pyodbc, pymssql, time
    from os import cpu_count
    from math import ceil
    from requests import Session
    from requests.adapters import HTTPAdapter
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, Future, as_completed, wait
    from cursor_FSS import file_open, file_save
    from helper_logger import Logger
    from sql import SQL
    from credentials_default import tms_databases, tms_dsn, tms_user, tms_password
except ImportError as error:
    print(error)

THREAD_POOL = 16

session = Session()
session.mount('https://', HTTPAdapter(pool_maxsize=THREAD_POOL, max_retries=3, pool_block=True))

class TMS:
    """
    Provides The Museum System interactivity

    Class variables
    ----------
    - THREAD_POOL (int) : number of threads to start per process in multithreading situation (default = 16)
    - session (HTTPAdapter) : external connections to DRS
    
    Methods
    -------
    - check_driver() -> none : checks if connections can be made to TMS
    - fetch(statement=str, query=str) -> tuple(list, list) : return data from TMS or local tables
    - tables(module_type=str) -> list, list : executes all queries related to a particular module
    - get_drs_metadata(urls=list) -> dict : starts multiple processes to batch download a large number of urls

    Private Helper Methods
    ---------------
    - __process(urls=list) -> dict
    - __get_drs_record(url=dict) -> (str, Response)
    """
    def __init__(self):
        self.cursor = None
        self.databases = {}
        self.valid = False
        self.driver = None

        self.logger = Logger('tms')
    
    def check_driver(self):
        """
        Checks if connections can be made to TMS. This requires a direct connection into the Harvard infrastructure.
        The method checks two different connection packages: pyodbc and pymssql (pyodbc was unsuccessful on my computer).
        """
        try:            
            for database in tms_databases:
                try:
                    self.driver = pyodbc.connect(f'DSN={tms_dsn};UID={tms_user};PWD={tms_password};DATABASE={database};')                   
                except Exception as e:
                    self.logger.log("Failed to connect to TMS with pyodbc")
                    self.logger.log(e)
                    try:
                        self.driver = pymssql.connect(tms_dsn, tms_user, tms_password, database)
                    except Exception as e:
                        self.logger.log("Failed to connect to TMS with pymssql")
                        self.logger.log(e)
                        return False
                if self.driver:
                    self.logger.log("CHECK DRIVER SUCCESSFUL")
                    self.logger.log(self.driver)
                    return True
        except:
            self.logger.log("CHECK DRIVER FAILED")
            return False

    def fetch(self, statement:str, query:str):
        """
        This method aims to collect data from TMS, or if unsuccesful, will attempt to load data from tables on disk instead.

        Parameters
        ----------
        - statement (str) : SQL statement to be executed
        - query (str) : name of the query

        Returns
        -------
        - tuple (list, list): rows, columns
        """
        try:
            self.logger.log(f'>>> DOWNLOADING SQL-QUERY "{query.upper()}"')
            cursor = self.driver.cursor()
            cursor.execute(statement)
            data = cursor.fetchall()
            if len(data):
                return ([[str(x) if x != None else "NULL" for x in row] for row in [list(row) for row in data]], [column[0] for column in cursor.description])
            else:

                # WE TRY AND LOAD A LOCAL COPY OF THE TABLE
                try:
                    table = file_open('tables', query, query.split('_')[0], True)
                    if table:
                        return table
                    else:
                        raise
                except:
                    raise
        except:
            print("Could not successfully connect to TMS: please make sure you have your connections parameters set correctly.")
            raise

    def tables(self, module:str, tables:bool=None):
        """
        Executes all queries related to a particular module.

        Parameters
        ----------
        - module_type (str) : name of the calling module

        Returns
        -------
        - first_record (list) : results of the first query
        - data (list): list of lists with results of subsequent queries
        """

        first_record, data = local_tables(module)

        if not first_record or not data:
            first_record, data = self.remote_tables(module, tables)

        return first_record, data

    def remote_tables(self, module, tables):
        try:
            first_record, data = {}, []

            for key, stmt in SQL[module].items():
                
                rows, cols = self.fetch(stmt, key)

                if tables:
                    file_save('tables', key, { 'rows' : rows, 'cols' : cols }, module)

                if key == module:
                    first_record['key'] = key
                    first_record['rows'] = rows
                    first_record['cols'] = cols
                else:
                    data.append({ 'key' : key, 'rows' : rows, 'cols' : cols })
            
            return first_record, data
        except:
            raise

def local_tables(module:str):
    """
    Executes all queries related to a particular module.

    Parameters
    ----------
    - module_type (str) : name of the calling module

    Returns
    -------
    - first_record (list) : results of the first query
    - data (list): list of lists with results of subsequent queries
    """
    # try:
    first_record, data = {}, []

    for key, stmt in SQL[module].items():
        
        # CHECK IF TABLES ARE STORED ON HARD DISK AND USE THOSE INSTEAD TO SPEED THINGS UP
        file = file_open('tables', key, module, True)
        
        if not file:
            return False, False

        rows, cols = file['rows'], file['cols']

        if key == module:
            first_record['key'] = key
            first_record['rows'] = rows
            first_record['cols'] = cols
        else:
            data.append({ 'key' : key, 'rows' : rows, 'cols' : cols })
    
    return first_record, data

def get_drs_metadata(urls:list):
    """
    Starts multiple processes to batch download a large number of urls
    
    Parameters
    ----------
    - urls (list) : urls to be processed

    Returns
    -------
    - dict : dictionary with drs id and nested dictionary with width and height properties.
    """

    workers = int((cpu_count()/2)-1)
    batch_size = ceil(len(urls)/workers)
    batch_results, futures = [], []

    def progress_indicator(future:Future):
        """ 
        This local method aggregates all results from each process and its threads 
        
        Parameters
        ----------
        - future (Future) : a Future object from concurrent.futures
        """
        try:
            batch_results.append(future.result())
        except:
            raise TypeError("DRS returned a NoneType object")

    # BATCH DOWNLOAD DRS METADATA IN MULTIPLE PROCESSES WITH MULTIPLE THREADS
    with ProcessPoolExecutor(max_workers=workers) as executor:
        batches = [urls[i:i+batch_size] for i in range(0, len(urls), batch_size)]
        for batch in batches:
            future = executor.submit(__process, batch)
            futures.append(future)
            future.add_done_callback(progress_indicator)

    done, not_done = wait(futures)

    return { k : v  for result in batch_results for k, v in result.items() if 'error' not in v }

def __process(urls:list):
    """
    Private method that processes a list of urls in a multithreading environment.
    
    Parameters
    ----------
    - urls (list) : urls to be processed

    Returns
    -------
    - dict : dictionary with results from multithreading jobs
    """
    try:
        results = {}
        with ThreadPoolExecutor(max_workers=THREAD_POOL) as executor:
            jobs = [executor.submit(__get_drs_record, *url) for url in zip(urls)]
            for out in as_completed(jobs):
                idx, response = out.result()
                if response.status_code == 200:
                    response = response.json()
                    results[idx] = { 'width' : response['width'], 'height' : response['height'] }
                else:
                    results[idx] = 'error'
        return results
    except:
        raise

def __get_drs_record(url:dict):
    """
    Private method that processes a single url in a multithreading environment.
    
    Parameters
    ----------
    - url (dict) : url object to be processed

    Returns
    -------
    - str : the drs id stored in the input url
    - Response : the response retrieved from drs at the designated url
    """
    try:
        response = session.get(url['url'])
        if response.status_code != 200:
            time.sleep(5)
            response = session.get(url['url'])
        return url['id'], response
    except:
        raise