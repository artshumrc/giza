
import argparse
import getpass
import constituents
import iiif_manifests
import media
import objects
import published
import sites
import sys

def str2bool(v):
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def main():
	CURSOR = None

	parser = argparse.ArgumentParser(description='Run all TMS data ingest scripts')
	parser.add_argument('-u','--username', help='TMS Username', required=False, default='RC\\svc-giza')
	parser.add_argument('-p','--password', help='TMS Password', required=False)
	parser.add_argument('-i','--iiif', type=str2bool, help='Run IIIF Manifests script', required=False, default=False)
	parser.add_argument('-s','--sites', type=str2bool, help='Run Sites script', required=False, default=True)
	parser.add_argument('-o','--objects', type=str2bool, help='Run Objects script', required=False, default=True)
	parser.add_argument('-c','--constituents', type=str2bool, help='Run Constituents script', required=False, default=True)
	parser.add_argument('-b','--published', type=str2bool, help='Run Published script', required=False, default=True)
	parser.add_argument('-m','--media', type=str2bool, help='Run Media script', required=False, default=True)
	args = vars(parser.parse_args())

	try:
		import pyodbc
		dsn = 'gizadatasource'
		user = args['username']
		if args['password']:
			password = args['password']
		else:
			password = getpass.getpass()
		database = 'gizacardtms'

		connection_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, user, password, database)
		connection = pyodbc.connect(connection_string)
		CURSOR = connection.cursor()
	except:
		print("Could not connect, no cursor")

	if args['iiif']:
		iiif_manifests.main(CURSOR)
	if args['sites']:
		sites.main(CURSOR)
	if args['objects']:
		objects.main(CURSOR)
	if args['constituents']:
		constituents.main(CURSOR)
	if args['published']:
		published.main(CURSOR)
	if args['media']:
		media.main(CURSOR)

if __name__ == "__main__":
   main()
