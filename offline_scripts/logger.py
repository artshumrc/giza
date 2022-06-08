from datetime import datetime
from cursor_FSS import file_save

TASKS = {
    'iiif' : 'IIIF Media manifests',
    'iiif_photographers' : 'IIIF Photographer manifests',
    'sites': 'Site records',
    'sites_dates': 'Site Dates records', 
    'sites_altnums': 'Site Altnums records', 
    'sites_objects': 'Site Objects records', 
    'sites_constituents': 'Site Constituent records', 
    'sites_published': 'Site Published records', 
    'sites_media': 'Site Media records',
    'objects' : 'Object records',
    'objects_altnums' : 'Object Alternate Number records',
    'objects_flexfields' : 'Object Flexfields records',
    'objects_sites' : 'Object Sites records', 
    'objects_constituents' : 'Object Constituent records',
    'objects_published' : 'Object Published records',
    'objects_unpublished' : 'Object Unpublished records',
    'objects_media' : 'Object Media records',
    'objects_geocodes' : 'Object Geocode records',
    'constituents' : 'Constituent records',
    'constituents' : '',
    'published' : '',
    'media' : '',
}

		# if args['ii

class Logger:
    
    def __init__(self, module_type):
        self.tasks = {}
        self.time_start = datetime.now()
        self.module_type = module_type

    def save_log(self, results, module):
        for filename, data in results.items():
            file_save('logs', filename, data, module)

    def log(self, message, module=None, results=None, end=False):
        if message and message not in self.tasks.values():
            message = f"{datetime.now()}: {message}"
            self.tasks[datetime.now()] = message
            print(message, end="\r", flush=True) if end else print(message)
            if module and results:
                self.save_log(results, module)
        # else:
            # self.tasks.remove(module)
            # if module in TASKS:
                # print(f"{datetime.now()}: {TASKS[module]} ({'done' if action == None else action})")
    
    def end(self):
        self.log(f'>>> ALL DONE (TOTAL RUNTIME {datetime.now()-self.start})')