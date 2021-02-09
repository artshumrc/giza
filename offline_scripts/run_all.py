
import argparse
import getpass
import constituents
import iiif_manifests
import media
import objects
import published
import sites
import sys

def main():
	CURSOR = None

	parser = argparse.ArgumentParser(description='Run all TMS data ingest scripts')
	parser.add_argument('-u','--username', help='TMS Username', required=False, default='RC\\rsinghal')
	parser.add_argument('-p','--password', help='TMS Password', required=False)
	parser.add_argument('-i','--iiif', help='Run IIIF Manifests script', required=False, default=False)
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
	sites.main(CURSOR)
	objects.main(CURSOR)
	constituents.main(CURSOR)
	published.main(CURSOR)
	media.main(CURSOR)

if __name__ == "__main__":
   main()
