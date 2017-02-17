import getpass
import constituents
import media
import objects
import published
import sites

CURSOR = None
if __name__ == "__main__":
    try:
    	import pyodbc
    	dsn = 'gizadatasource'
    	user = 'RC\\rsinghal'
    	password = getpass.getpass()
    	database = 'gizacardtms'

    	connection_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, user, password, database)
    	connection = pyodbc.connect(connection_string)
    	CURSOR = connection.cursor()
    except:
        print "Could not connect, no cursor"

    sites.main(CURSOR)
    objects.main(CURSOR)
    constituents.main(CURSOR)
    published.main(CURSOR)
    media.main(CURSOR)
