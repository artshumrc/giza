import csv
import elasticsearch_connection
import json
import os
from datetime import datetime
import getpass

import media_sql
from utils import generate_iiif_manifest, generate_multi_canvas_iiif_manifest
from classifications import MEDIATYPES

ELASTICSEARCH_INDEX = 'iiif'
ARCH_IDS = {}
SITE_RELATIONS = {}

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
		print("Going to execute sql command")
		print(datetime.now())
		CURSOR.execute(sql_command)
		print("Finished executing sql command")
		print(datetime.now())
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			print("Going to process media row")
			print(datetime.now())
			process_media_row()
			print("Finished processing media row")
			print(datetime.now())
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

def process_sites_objects_related_manifests():
	def get_indices():
		indices = {
			'site_id_index' : columns.index('SiteID'),
			'classification_id_index' : columns.index('ClassificationID'),
			'object_id_index' : columns.index('ObjectID'),
			'object_title_index' : columns.index('Title'),
			'object_number_index' : columns.index('ObjectNumber'),
			'object_date_index' : columns.index('ObjectDate'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName'),
			'drs_id' : columns.index('ArchIDNum')
		}
		return indices

	with open(os.path.join(DIRNAME, '..', 'data', 'sites_objects_related.csv'), 'r', encoding="utf-8-sig") as csvfile:
		# Get the query headers to use as keys in the JSON
		headers = next(csvfile)
		headers = headers.replace('\r\n','')
		headers = headers.replace('\n','')
		columns = headers.split(',')
		indices = get_indices()

		rows = csv.reader(csvfile, delimiter=',', quotechar='"')
		object = {}
		for row in rows:
			if row[indices['drs_id']].lower() == "null":
				continue
			if row[indices['drs_id']] not in ARCH_IDS.keys():
				manifest_ob = {
					"ArchIDNum": row[indices['drs_id']],
					"Description": row[indices['object_title_index']],
					"MediaView": row[indices['object_number_index']]
				}
				object = {
					"id": row[indices['drs_id']],
					"manifest": generate_iiif_manifest(manifest_ob)
				}
				save(object)
				resource = object['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']
				ARCH_IDS[row[indices['drs_id']]] = resource
			if row[indices['site_id_index']] not in SITE_RELATIONS.keys():
				SITE_RELATIONS[row[indices['site_id_index']]] = {
					'description': row[indices['object_title_index']],
					'label': row[indices['object_number_index']],
					'resources': [
						ARCH_IDS[row[indices['drs_id']]]
					]
				}
			else:
				SITE_RELATIONS[row[indices['site_id_index']]]['resources'].append(
					ARCH_IDS[row[indices['drs_id']]]
				)



def process_sites_media_related_manifests():
	def get_indices():
		indices = {
			'site_id_index' : columns.index('SiteID'),
			'media_master_id_index' : columns.index('MediaMasterID'),
			'primary_display_index' : columns.index('PrimaryDisplay'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'rendition_number_index' : columns.index('RenditionNumber'),
			'description_index' : columns.index('Description'),
			'caption_index' : columns.index('PublicCaption'),
			'media_view_index' : columns.index('MediaView'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName'),
			'main_path_index' : columns.index('MainPathName'),
			'main_file_index' : columns.index('MainFileName'),
			'drs_id' : columns.index('ArchIDNum')
		}
		return indices



	with open(os.path.join(DIRNAME, '..', 'data', 'sites_media_related.csv'), 'r', encoding="utf-8-sig") as csvfile:
		# Get the query headers to use as keys in the JSON
		headers = next(csvfile)
		headers = headers.replace('\r\n','')
		headers = headers.replace('\n','')
		columns = headers.split(',')
		indices = get_indices()

		rows = csv.reader(csvfile, delimiter=',', quotechar='"')
		object = {}

		for row in rows:
			if row[indices['drs_id']].lower() == "null":
				continue
			if row[indices['drs_id']] not in ARCH_IDS.keys():
				manifest_ob = {
					"ArchIDNum": row[indices['drs_id']],
					"Description": row[indices['description_index']],
					"MediaView": row[indices['media_view_index']]
				}
				object = {
					"id": row[indices['drs_id']],
					"manifest": generate_iiif_manifest(manifest_ob)
				}
				save(object)
				resource = object['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']
				ARCH_IDS[row[indices['drs_id']]] = resource
			if row[indices['site_id_index']] not in SITE_RELATIONS.keys():
				SITE_RELATIONS[row[indices['site_id_index']]] = {
					'description': row[indices['description_index']],
					'label': row[indices['media_view_index']],
					'resources': [
						ARCH_IDS[row[indices['drs_id']]]
					]
				}
			else:
				SITE_RELATIONS[row[indices['site_id_index']]]['resources'].append(
					ARCH_IDS[row[indices['drs_id']]]
				)

			## MOVE TO media.py ##
			# try to get the media document and append the drs_id
			media_id = row[indices['media_master_id_index']]
			media_type_key = int(row[indices['media_type_id_index']])
			media_type = MEDIATYPES.get(media_type_key)

			media = {}
			if elasticsearch_connection.item_exists(media_id, media_type, ELASTICSEARCH_INDEX):
				media = elasticsearch_connection.get_item(media_id, media_type, ELASTICSEARCH_INDEX)
				media['drsId'] = row[indices['drs_id']]
				save_media(media)
			else:
				print("%s could not be found!" % media_id)
			## MOVE TO media.py ##



def process_object_sites_related_manifests():
	def get_indices():
		indices = {
			'id_index' : columns.index('ID'),
			'site_id_index' : columns.index('SiteID'),
			'site_name_index' : columns.index('SiteName'),
			'site_number_index' : columns.index('SiteNumber'),
			'classification_id_index' : columns.index('ClassificationID'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName'),
			'drs_id' : columns.index('ArchIDNum')
		}
		return indices


	with open(os.path.join(DIRNAME, '..', 'data', 'objects_sites_related.csv'), 'r', encoding="utf-8-sig") as csvfile:
		# Get the query headers to use as keys in the JSON
		headers = next(csvfile)
		headers = headers.replace('\r\n','')
		headers = headers.replace('\n','')
		columns = headers.split(',')
		indices = get_indices()

		rows = csv.reader(csvfile, delimiter=',', quotechar='"')
		object = {}
		for row in rows:
			if row[indices['drs_id']].lower() == "null":
				continue
			if row[indices['drs_id']] not in ARCH_IDS.keys():
				manifest_ob = {
					"ArchIDNum": row[indices['drs_id']],
					"Description": row[indices['site_name_index']],
					"MediaView": row[indices['site_number_index']]
				}
				object = {
					"id": row[indices['drs_id']],
					"manifest": generate_iiif_manifest(manifest_ob)
				}
				save(object)
				resource = object['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']
				ARCH_IDS[row[indices['drs_id']]] = resource
			if row[indices['site_id_index']] not in SITE_RELATIONS.keys():
				SITE_RELATIONS[row[indices['site_id_index']]] = {
					'description': row[indices['site_name_index']],
					'label': row[indices['site_number_index']],
					'resources': [
						ARCH_IDS[row[indices['drs_id']]]
					]
				}
			else:
				SITE_RELATIONS[row[indices['site_id_index']]]['resources'].append(
					ARCH_IDS[row[indices['drs_id']]]
				)


def process_object_media_related_manifests():
	def get_indices():
		indices = {
			'id_index' : columns.index('ID'),
			'media_master_id_index' : columns.index('MediaMasterID'),
			'classification_id_index' : columns.index('ClassificationID'),
			'primary_display_index' : columns.index('PrimaryDisplay'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'rendition_number_index' : columns.index('RenditionNumber'),
			'description_index' : columns.index('Description'),
			'caption_index' : columns.index('PublicCaption'),
			'media_view_index' : columns.index('MediaView'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName'),
			'main_path_index' : columns.index('MainPathName'),
			'main_file_index' : columns.index('MainFileName'),
			'drs_id' : columns.index('ArchIDNum')
		}
		return indices

	with open(os.path.join(DIRNAME, '..', 'data', 'objects_media_related.csv'), 'r', encoding="utf-8-sig") as csvfile:
		# Get the query headers to use as keys in the JSON
		headers = next(csvfile)
		headers = headers.replace('\r\n','')
		headers = headers.replace('\n','')
		columns = headers.split(',')
		indices = get_indices()

		rows = csv.reader(csvfile, delimiter=',', quotechar='"')
		object = {}
		for row in rows:
			if not row[indices['drs_id']].lower() == "null" and row[indices['drs_id']] not in ARCH_IDS.keys():
				manifest_ob = {
					"ArchIDNum": row[indices['drs_id']],
					"Description": row[indices['description_index']],
					"MediaView": row[indices['media_view_index']]
				}
				object = {
					"id": row[indices['drs_id']],
					"manifest": generate_iiif_manifest(manifest_ob)
				}
				save(object)
				resource = object['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']
				ARCH_IDS[row[indices['drs_id']]] = resource
			elif not row[indices['drs_id']].lower() == "null":
				# try to get the media document and append the drs_id
				media_id = row[indices['media_master_id_index']]
				media_type_key = int(row[indices['media_type_id_index']])
				media_type = MEDIATYPES.get(media_type_key)

				media = {}
				if elasticsearch_connection.item_exists(media_id, media_type, ELASTICSEARCH_INDEX):
					media = elasticsearch_connection.get_item(media_id, media_type, ELASTICSEARCH_INDEX)
					media['drsId'] = row[indices['drs_id']]
					save_media(media)
				else:
					print("%s could not be found!" % media_id)

def compile_resources_by_site():
	print("Compiling associated site media for manifests.")
	for k, v in SITE_RELATIONS.items():
		object = {
		    "id": k,
			"manifest": generate_multi_canvas_iiif_manifest(k, v)
		}
		save(object)
	print(f"Compiled resources for {len(SITE_RELATIONS)} sites.")


def save(manifest):
	if manifest and 'id' in manifest:
		elasticsearch_connection.add_or_update_item(manifest['id'], json.dumps(manifest), 'manifest', ELASTICSEARCH_INDEX)

def save_media(media):
	if media and 'id' in media:
		if not media['mediatype']:
			# ignore for now, but this should send an email notification that there is missing data
			# so that the classifications.py file can be updated
			print("%s is missing a media type, ignoring for now" % (media['id']))
			return
		elasticsearch_connection.add_or_update_item(media['id'], json.dumps(media), media['mediatype'], ELASTICSEARCH_INDEX)

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
	# process_sites_media_related_manifests()
	# process_object_media_related_manifests()
	# process_sites_objects_related_manifests()
	# process_object_sites_related_manifests()
	# compile_resources_by_site()

if __name__ == "__main__":
	main()
