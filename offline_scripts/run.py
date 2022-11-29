try:
	from argparse import ArgumentParser, ArgumentTypeError
	from cursor import Cursor
	from module import Module
except ImportError as error:
    print(error)

# DEFAULT MODULES IN A LIST
ALLOWED_MODULES = ['iiif', 'met', 'sites', 'objects', 'constituents', 'published', 'media']

REQUIRED_MODULES = ['iiif', 'met']
# OPTIONAL_MODULES = ['objects']
OPTIONAL_MODULES = ['sites', 'objects', 'constituents', 'published', 'media']
# OPTIONAL_MODULES = ['sites']

MODULES = REQUIRED_MODULES + OPTIONAL_MODULES

"""
Modules have two purposes:
1) generate individual records;
2) generate/update manifests for those records;

- Set --memory to True to only use in-memory storage for processing data.
- Set --drs to True to refresh the DRS tables.
- Set --tables to True to force a refresh of local tables for selected modules. This will delete the DRS table as well.
- Set --refresh to True to force a recompilation of selected modules.
- Set --es to True to push records to ElasticSearch. This will overwrite/replace existing records and reflect changes on the site.
- Set --th to batch download and store record thumbnails not yet in the file system.
- Set --tr to refresh all thumbnails, overwriting those already there.

NOTE: 
- 'published' and 'media' do not generate relations and do not produce manifests.
- The 'published' module triggers generation of a new library by default.
"""

def str2bool(v):
    if isinstance(v, bool): return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'): return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'): return False
    else: raise ArgumentTypeError('Boolean value expected.')

def main():
	try:
		parser = ArgumentParser(description='Run all TMS data ingest scripts')

		parser.add_argument('-m', '--modules', nargs="+", help='A list of modules to run: iiif, met, sites, objects, constituents, published and media', default=MODULES)
		parser.add_argument('-d', '--drs', type=str2bool, help='Refresh DRS', required=False, default=True)
		parser.add_argument('-mem', '--memory', type=str2bool, help='Avoid using compilations and run everything in-memory', required=False, default=True)
		parser.add_argument('-es', '--es', type=str2bool, help='Push updates to ES (MET compilations are not written to ES).', required=False, default=True)
		parser.add_argument('-p', '--push', type=str2bool, help='Push all data to ElasticSearch at the end of the program', required=False, default=True)
		parser.add_argument('-t','--tables', type=str2bool, help='Only store copies of the tables for later reuse', required=False, default=True)
		parser.add_argument('-th', '--thumbnails', type=str2bool, help='Batch download and store thumbnails in the Django static folder for quickly loading records', required=False, default=True)
		parser.add_argument('-r','--refresh', type=str2bool, help='Refresh JSON tables', required=False, default=False)
		parser.add_argument('-tr', '--thumbnails_refresh', type=str2bool, help='Refresh all thumbnails in the filesystem. This is a long operation!', required=False, default=False)
		parser.add_argument('-c','--compile', type=str2bool, help='Compile JSON files using local tables (if available)', required=False, default=True)
		parser.add_argument('-s', '--store', type=str2bool, help='Store a copy of the compiled files on disk', required=False, default=False)

		args = parser.parse_args()

		if any([module for module in MODULES if module not in ALLOWED_MODULES]) or any([module for module in REQUIRED_MODULES if module not in MODULES]):
			raise Exception('Incorrect module configuration')

		cursor = Cursor(args)

		cursor.check_connections()

		for module in args.modules:
			Module(MODULES, module, cursor, drs=args.drs, memory=args.memory, push=args.push, tables=args.tables, store=args.store, thumbnails=args.thumbnails, thumbnails_refresh=args.thumbnails_refresh, refresh=args.refresh, compile=args.compile, es=args.es) if module in ALLOWED_MODULES else print(f'>>> UNKNOWN MODULE: "{module}"')
	except Exception as e:
		print("There is a problem running this program.")
		print(e)

if __name__ == "__main__":
   main()