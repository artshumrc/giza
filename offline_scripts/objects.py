# eventually, this should be a live query from the SQL Server
# for now, use static files in the data/ directory

import csv
import codecs
import json
import elasticsearch_connection
import pyodbc
import getpass

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES

SAMPLE_OBJECTS = ('61198', '15332', '15059', '52264', '50823', '35634', '5614', '46942', '48325', '3461', '25389', '25501')

CURSOR = None

# First update each Object with the latest data
# This is the basic information/metadata that comprises a Object
def process_objects():
	print "Starting Objects..."
	if CURSOR:
		sql_command = """
		SELECT Objects.ObjectID, Objects.ObjectNumber, Objects.ObjectStatusID, Objects.ClassificationID, Objects.ObjectName + ',,' as ObjectOwnerDetails,
		Objects.Dated as EntryDate, replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.Medium + ',,' as Medium, 
		Objects.Dimensions + ',,' as Dimensions, Objects.CreditLine, Objects.Description + ',,' AS Description, Objects.Provenance, 
		Objects.PubReferences + ',,' AS PubReferences
		FROM Objects 
		LEFT JOIN ObjTitles on Objects.ObjectID=ObjTitles.ObjectID
		WHERE Objects.PublicAccess = 1
		AND Objects.ObjectID >= 0
		ORDER BY Objects.ObjectID
		"""
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		(object_id_index, classification_id_index, object_number_index) = get_indices(columns)

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = []
			for x in cursor_row:
				if isinstance(x, int):
					row.append(str(x))
				elif isinstance(x, unicode):
					row.append(x.encode('utf-8'))
				else:
					row.append(str(x))
			(object, current_id) = process_object_row(row, object, current_id, columns, object_id_index, classification_id_index, object_number_index)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(object)

	else:
		with open('../data/objects.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			(object_id_index, classification_id_index, object_number_index) = get_indices(columns)

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(row, object, current_id, columns, object_id_index, classification_id_index, object_number_index)
			# save last object to elasticsearch
			save(object)
	
	print "Finished Objects..."

def get_indices(columns):
	object_id_index = columns.index('ObjectID')
	classification_id_index = columns.index('ClassificationID')
	object_number_index = columns.index('ObjectNumber')
	return (object_id_index, classification_id_index, object_number_index)

def save(object):
	if object:
		elasticsearch_connection.add_or_update_item(object['objectid'], json.dumps(object), object['classification'])

def process_object_row(row, object, current_id, columns, object_id_index, classification_id_index, object_number_index):
	object_id = row[object_id_index]
	classification_key = int(row[classification_id_index])
	classification = CLASSIFICATIONS.get(classification_key)

	if object_id not in SAMPLE_OBJECTS:
		return (object, current_id)

	# I don't think there are any duplicate rows for objects, but keep it here since it doesn't break anything
	if object_id != current_id:
		save(object)
		current_id = object_id
		object = {}

	object['classification'] = classification
	# loop through each row
	for index, value in enumerate(columns):
		key = value.lower()
		row_value = row[index]

		# cleanup row data
		if row_value.isdigit():
			row_value = int(row_value)
		elif row_value == "NULL":
			row_value = None
		else:
			row_value = row_value.replace(',,','')

		if 'title' in key:
			object_title = row_value
			if classification == "diarypages" and object_title is None:
				object_number = row[object_number_index]
				idx = object_number.find('_')
				object_title = object_number[idx+1:]
				object[key] = object_title
			else:
				object[key] = row_value
		else:
			object[key] = row_value
	return (object, current_id)

if __name__ == "__main__":
	try:
		dsn = 'gizadatasource'
		user = 'RC\\rsinghal'
		password = getpass.getpass()
		database = 'gizacardtms'

		connection_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, user, password, database)
		connection = pyodbc.connect(connection_string)
		CURSOR = connection.cursor()
	except:
		print "Could not connect to gizacardtms, defaulting to CSV files"

	process_objects()