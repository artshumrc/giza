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
			'media_type_id_index' : columns.index('MediaTypeID'),
			'description_index' : columns.index('Description'),
			'media_view_index' : columns.index('MediaView'),
			'caption_index' : columns.index('PublicCaption'),
			'drs_id' : columns.index('ArchIDNum')
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
		drs_id = "" if row[indices['drs_id']].lower() == "null" else row[indices['drs_id']]
		manifest_id = media_type + '-' + media_id

		if description == "":
			description = caption

		manifest_ob = {
			"ManifestID": manifest_id,
			"ArchIDNum": drs_id,
			"Description": description,
			"MediaView": mediaview
		}
		object = {
			"id": manifest_id,
			"manifest": generate_iiif_manifest(manifest_ob)
		}
		save(object)
		resource = object['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']


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
				process_media_row()

	print("Finished Media IIIF...")
	print(datetime.now())

def save(manifest):
	if manifest and 'id' in manifest:
		elasticsearch_connection.add_or_update_item(manifest['id'], json.dumps(manifest), 'manifest', ELASTICSEARCH_INDEX)

def main(CURSOR=None):
	if not CURSOR:
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
			print("Could not connect to gizacardtms, defaulting to CSV files")

	process_media_iiif(CURSOR)

if __name__ == "__main__":
	main()
