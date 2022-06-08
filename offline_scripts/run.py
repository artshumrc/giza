try:
	from argparse import ArgumentParser, ArgumentTypeError
	from cursor import Cursor
	from module import Module
except ImportError as error:
    print(error)

# STORE YOUR FAVORITE MODULES IN A LIST
# MODULES = ['iiif', 'met', 'sites', 'objects', 'constituents', 'published', 'media']
# MODULES = ['met', 'sites', 'objects', 'constituents', 'published', 'media']
# MODULES = ['sites', 'objects', 'constituents', 'published', 'media']
# MODULES = ['objects', 'constituents', 'published', 'media']
# MODULES = ['constituents', 'published', 'media']
MODULES = ['published', 'media']
# MODULES = ['media']
# MODULES = ['met']
# MODULES = ['iiif', 'met', 'sites', 'objects', 'constituents', 'published']
# MODULES = ['iiif', 'met', 'sites', 'objects', 'constituents']
# MODULES = ['iiif', 'met', 'sites', 'objects']
# MODULES = ['iiif', 'met', 'sites']
# MODULES = ['iiif', 'met']
# MODULES = ['iiif']

ALLOWED_MODULES = ['iiif', 'met', 'sites', 'objects', 'constituents', 'published', 'media']

def str2bool(v):
    if isinstance(v, bool): return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'): return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'): return False
    else: raise ArgumentTypeError('Boolean value expected.')

def main():
	parser = ArgumentParser(description='Run all TMS data ingest scripts')

	parser.add_argument('-m', '--modules', nargs="+", help='A list of modules to run: iiif, met, sites, objects, constituents, published and media', default=MODULES)
	parser.add_argument('-mem', '--memory', type=str2bool, help='Avoid using compilations and run everything in-memory', required=False, default=True)
	parser.add_argument('-es', '--es', type=str2bool, help='Push updates to ES (MET compilations are not written to ES).', required=False, default=True)
	parser.add_argument('-p', '--push', type=str2bool, help='Push all data to ElasticSearch at the end of the program', required=False, default=True)
	parser.add_argument('-t','--tables', type=str2bool, help='Only store copies of the tables for later reuse', required=False, default=True)
	parser.add_argument('-r','--refresh', type=str2bool, help='Refresh JSON tables', required=False, default=False)
	parser.add_argument('-c','--compile', type=str2bool, help='Compile JSON files using local tables (if available)', required=False, default=False)
	parser.add_argument('-s', '--store', type=str2bool, help='Store a copy of the compiled files on disk', required=False, default=False)	

	args = parser.parse_args()

	cursor = Cursor()

	if cursor.check_connections():
		"""
		Modules have two purposes:
		1) generate individual records;
		2) generate/update manifests for those records;

		- Set --memory to True to only use in-memory storage for processing data.
		- Set --tables to True to force a refresh of local tables for selected modules.
		- Set --refresh to True to force a recompilation of selected modules.
		- Set --es to True to push records to ElasticSearch. This will overwrite/replace existing records.

		NOTE: 
		- 'published' and 'media' do not generate relations and do not produce manifests.
		- The 'published' module triggers generation of a new library by default.
		"""

		for module in args.modules:
			Module(module, cursor, memory=args.memory, push=args.push, tables=args.tables, store=args.store, refresh=args.refresh, compile=args.compile, es=args.es) if module in ALLOWED_MODULES else print(f'>>> UNKNOWN MODULE: "{module}"')
		
	else:
		print(f"There is no point running this program without access to TMS data and an instance of ElasticSearch.")

if __name__ == "__main__":
   main()