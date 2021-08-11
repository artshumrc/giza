import csv
import elasticsearch_connection
import json
import os
from datetime import datetime
import getpass

import media_sql
from utils import process_cursor_row, generate_iiif_manifest
from classifications import MEDIATYPES

ELASTICSEARCH_INDEX = 'iiif'

DIRNAME = os.path.dirname(__file__)

def process_media_iiif(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('MediaMasterID'),
			'rendition_number_index' : columns.index('RenditionNumber'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'description_index' : columns.index('Description'),
			'media_view_index' : columns.index('MediaView'),
			'caption_index' : columns.index('PublicCaption'),
			'drs_id' : columns.index('ArchIDNum'),
			'department_index' : columns.index('Department'),
			'date_index' : columns.index('DateOfCapture'),
			'problems_index' : columns.index('ProblemsQuestions')
		}
		return indices

	def process_media_row():
		media_id = row[indices['id_index']]
		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)

		# ignore non-photos, if they somehow managed to show up in the query results
		if media_type_key != 1:
			return

		description = "" if row[indices['description_index']].lower() == "null" else row[indices['description_index']]
		mediaview = "" if row[indices['media_view_index']].lower() == "null" else row[indices['media_view_index']]
		caption = "" if row[indices['caption_index']].lower() == "null" else row[indices['caption_index']]
		subjects = ": ".join([mediaview, caption])
		drs_id = "" if row[indices['drs_id']].lower() == "null" else row[indices['drs_id']]
		number = "" if row[indices['rendition_number_index']].lower() == "null" else row[indices['rendition_number_index']]
		department = "" if row[indices['department_index']].lower() == "null" else row[indices['department_index']]
		date = "" if row[indices['date_index']].lower() == "null" else row[indices['date_index']]
		problemsquestions = "" if row[indices['problems_index']].lower() == "null" else row[indices['problems_index']]
		manifest_id = media_type + '-' + media_id

		metadata = []
		if number:
			metadata.append({'label' : 'ID',
			'value' : number})
		if department:
			metadata.append({'label' : 'Department',
			'value' : department})
		if subjects:
			metadata.append({'label' : 'Subjects',
			'value' : subjects})
		if date:
			metadata.append({'label' : 'Date',
			'value' : date})
		if problemsquestions:
			metadata.append({'label' : 'Problems/Questions',
			'value' : problemsquestions})

		if description == "":
			description = caption

		manifest_ob = {
			"manifest_id": manifest_id,
			"drs_id": drs_id,
			"description": description,
			"label": mediaview,
			"metadata": metadata
		}

		## see if manifest exists to grab the existing resource data so we can avoid checking the CSV file or doing a network call to IDS
		if elasticsearch_connection.item_exists(media_type+'-'+media_id, 'manifest', ELASTICSEARCH_INDEX):
			existing_manifest = elasticsearch_connection.get_item(media_type+'-'+media_id, 'manifest', ELASTICSEARCH_INDEX)
			resource = existing_manifest['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']
			if drs_id in resource['@id']:
				manifest_ob['resource'] = resource

		object = {
			"id": manifest_id,
			"manifest": generate_iiif_manifest(manifest_ob)
		}
		save(object)

	print("Starting Media IIIF...")
	print(datetime.now())
	if CURSOR:
		sql_command = media_sql.MEDIA_IIIF
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			process_media_row()
			cursor_row = CURSOR.fetchone()

	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'media_iiif.csv'), 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			for row in rows:
				print("Going to process manifest row")
				print(datetime.now())
				process_media_row()
				print("Finished processing manifest row")
				print(datetime.now())

	print("Finished Media IIIF...")
	print(datetime.now())

def process_media_photographers(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('MediaMasterID'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'role_index' : columns.index('Role'),
			'display_name_index' : columns.index('DisplayName'),
			'display_date_index' : columns.index('DisplayDate')
		}
		return indices

	def process_media_row(manifest, current_id):
		media_id = row[indices['id_index']]
		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)
		manifest_id = media_type + '-' + media_id

		# ignore non-photos, if they somehow managed to show up in the query results
		if media_type_key != 1:
			return(manifest, current_id)

		if manifest_id != current_id:
			save(manifest)
			current_id = manifest_id
			manifest = {}
			if elasticsearch_connection.item_exists(manifest_id, 'manifest', ELASTICSEARCH_INDEX):
				manifest = elasticsearch_connection.get_item(manifest_id, 'manifest', ELASTICSEARCH_INDEX)
			else:
				print("%s could not be found!" % manifest_id)
				return(manifest, current_id)

		role = "" if row[indices['role_index']].lower() == "null" else row[indices['role_index']]
		display_name = "" if row[indices['display_name_index']].lower() == "null" else row[indices['display_name_index']]
		display_date = "" if row[indices['display_date_index']].lower() == "null" else row[indices['display_date_index']]

		if display_date:
			value = display_name + ", " + display_date
		else:
			value = display_name
		manifest['manifest']['metadata'].append({'label' : role, 'value' : value})

		return(manifest, current_id)


	print("Starting Media IIIF Photographers...")
	print(datetime.now())
	if CURSOR:
		sql_command = media_sql.MEDIA_IIIF_PHOTOGRAPHERS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		manifest = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			# print("Going to process manifest photographer row")
			# print(datetime.now())
			(manifest, current_id) = process_media_row(manifest, current_id)
			# print("Finished processing manifest photographer row")
			# print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last manifest to elasticsearch
		save(manifest)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'media_iiif_photographers.csv'), 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			manifest = {}
			current_id = '-1'
			for row in rows:
				(manifest, current_id) = process_media_row(manifest, current_id)
			# save last manifest to elasticsearch
			save(manifest)

	print("Finished Media IIIF Photographers...")
	print(datetime.now())

def save(manifest):
	if manifest and 'id' in manifest:
		elasticsearch_connection.add_or_update_item(manifest['id'], json.dumps(manifest), 'manifest', ELASTICSEARCH_INDEX)

def main(CURSOR=None):
	if not CURSOR:
		try:
			import pyodbc
			dsn = 'gizadatasource'
			user = 'RC\\svc-giza'
			password = getpass.getpass()
			database = 'gizacardtms'

			connection_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, user, password, database)
			connection = pyodbc.connect(connection_string)
			CURSOR = connection.cursor()
		except:
			print("Could not connect to gizacardtms, defaulting to CSV files")

	process_media_iiif(CURSOR)
	process_media_photographers(CURSOR)

if __name__ == "__main__":
	main()
