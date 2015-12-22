# eventually, this should be a live query from the SQL Server
# for now, use static files in the data/ directory

import csv
import codecs
import json
import elasticsearch_connection
import pyodbc

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES

SAMPLE_OBJECTS = ('61198', '15332', '15059', '52264', '50823', '35634', '5614', '46942', '48325', '3461', '25389', '25501')

# First update each Object with the latest data
# This is the basic information/metadata that comprises a Object
print "Starting objects.csv..."
with open('../data/objects.csv', 'rb') as csvfile:
	# Get the query headers to use as keys in the JSON
	headers = next(csvfile)
	if headers.startswith(codecs.BOM_UTF8):
		headers = headers[3:]
	headers = headers.replace('\r\n','')
	columns = headers.split(',')
	object_id_index = columns.index('ObjectID')
	classification_id_index = columns.index('ClassificationID')
	object_title_index = columns.index('Title')
	object_number_index = columns.index('ObjectNumber')

	rows = csv.reader(csvfile, delimiter=',', quotechar='"')

	object = {}
	current_id = '-1'
	for row in rows:
		object_id = row[object_id_index]
		classification_key = int(row[classification_id_index])
		classification = CLASSIFICATIONS.get(classification_key)

		#if object_id not in SAMPLE_OBJECTS:
		#	continue
		
		# I don't think there are any duplicate rows for objects, but keep it here since it doesn't break anything
		if object_id != current_id:
			if object:
				elasticsearch_connection.add_or_update_item(current_id, json.dumps(object), object['classification'])
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
	if object:
		# save last object to elasticsearch
		elasticsearch_connection.add_or_update_item(current_id, json.dumps(object), object['classification'])
print "Finished objects.csv..."
