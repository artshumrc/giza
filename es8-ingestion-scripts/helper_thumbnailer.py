from io import BytesIO
from base64 import b64encode
from os import cpu_count, path, makedirs, getcwd
from math import ceil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed, Future, wait
from requests.adapters import HTTPAdapter
from requests import Session
from PIL import Image
import environ

THREAD_POOL = 32

session = Session()
session.mount('https://', HTTPAdapter(pool_maxsize=THREAD_POOL, max_retries=3, pool_block=True))

def download_thumbnails(urls:list):
    """
    Starts multiple processes to batch download a large number of urls
    
    Parameters
    ----------
    - urls (list) : urls to be processed

    Returns
    -------
    - dict : dictionary with drs id and nested dictionary with width and height properties.
    """

    env = environ.Env()
    environ.Env.read_env()
    workers = env('CPU_WORKERS', default=int((cpu_count()/2)-1))
    batch_size = ceil(len(urls)/workers)
    batch_results, futures = [], []
    dir = f'static/images/thumbnails'

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
            future = executor.submit(__process, batch, dir)
            futures.append(future)
            future.add_done_callback(progress_indicator)

    done, not_done = wait(futures)

    res = [ k for result in batch_results for k, v in result.items() if 'error' not in v ]
    error = [ k for result in batch_results for k, v in result.items() if 'error' in v ]

    return res, error

def thumbnail(file, file_name):
    dir = path.join(getcwd(), 'static', 'media', 'thumbnails')
    if not path.exists(dir): makedirs(dir)
    
    # BUFFER FOR THE IMAGE
    buffer = BytesIO(file)
    thumb = Image.open(buffer)
    thumb.thumbnail((100, 100))

    # BUFFER FOR THE THUMBNAIL
    buf = BytesIO()
    
    # RESAVE THUMB TO BUFFER
    thumb.save(buf, format=thumb.format)
    
    # SAVE THUMB TO FS
    thumb.save(f'{path.join(dir, file_name)}.jpg', format=thumb.format)
    
    return buf

def __process(urls:list, folder:str=None):
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
            jobs = [executor.submit(__get_url, *url, folder) for url in zip(urls)]
            for out in as_completed(jobs):
                url, response = out.result()
                if response.status_code != 200:
                    results[url['Thumbnail_ID']] = 'error'
        return results
    except:
        raise

def __get_url(url:dict, folder:str=None):
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
        if response.status_code in [403, 404]:
            return url['Thumbnail_ID'], response
        while response.status_code != 200:
            response = session.get(url['url'])
            buffer = thumbnail(response.content, str(url['Thumbnail_ID']))
            url['base64'] = f'data:{response.headers["Content-Type"]};base64,{b64encode(buffer.getvalue()).decode("utf-8")}'
        # with open(f'{folder}/{url["Thumbnail_ID"]}.jpg', 'wb') as fobj:
            # fobj.write(response.content)
        return url, response
    except Exception as e:
        print(e)
        raise e