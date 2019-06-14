

import getpass
import constituents
import media
import objects
import published
import sites
import sys

CURSOR = None
if __name__ == "__main__":
	try:
		import pyodbc
		dsn = 'gizadatasource'
		user = 'RC\\rsinghal'
		if len(sys.argv) == 2:
			password = sys.argv[1]
		else:
			password = getpass.getpass()
		database = 'gizacardtms'

		connection_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, user, password, database)
		connection = pyodbc.connect(connection_string)
		CURSOR = connection.cursor()
	except:
		print("Could not connect, no cursor")

	# sites.main(CURSOR)
	# objects.main(CURSOR)
	# constituents.main(CURSOR)
	published.main(CURSOR)
	media.main(CURSOR)
