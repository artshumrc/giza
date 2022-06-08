# from base import Worker
from concurrent.futures import ThreadPoolExecutor, as_completed
import time, requests

THREAD_POOL = 16

session = requests.Session()
session.mount(
    'https://',
    requests.adapters.HTTPAdapter(pool_maxsize=THREAD_POOL,
                                  max_retries=3,
                                  pool_block=True)
)

# class Cursor_worker(Worker):

#     def __init__(self):
#         super().__init__()

def process(urls):
    results = {}
    # drs_records = len(urls)
    with ThreadPoolExecutor(max_workers=THREAD_POOL) as executor:
        for out in as_completed([executor.submit(get_drs_record, url) for url in urls]):
            idx, response = out.result()
            # drs_records = drs_records - 1
            # print(drs_records, end="\r", flush=True)
            if response.status_code == 200:
                response = response.json()
                results[idx] = { 'width' : response['width'], 'height' : response['height'] }
            else:
                results[idx] = 'error'
    return results

def get_drs_record(url):
    response = session.get(url['url'])
    if response.status_code != 200:
        time.sleep(5)
        response = session.get(url['url'])
    return url['id'], response