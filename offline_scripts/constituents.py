

from builtins import next
import csv
import codecs
import elasticsearch_connection
import getpass
import json
import operator
import os
from datetime import datetime

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES, MEDIATYPES
import constituents_sql
from utils import get_media_url, process_cursor_row, generate_iiif_manifest, generate_multi_canvas_iiif_manifest

ELASTICSEARCH_INDEX = 'giza'
ARCH_IDS = {}
CONSTITUENT_RELATIONS = {}

DIRNAME = os.path.dirname(__file__)

# First update each Constituent with the latest data
# This is the basic information/metadata that comprises a Constituent
def process_constituents(CURSOR):
	def get_indices():
		indices = {
			'constituent_id_index' : columns.index('ID'),
			'type_id_index' : columns.index('ConstituentTypeID')
		}
		return indices

	def process_constituent_row(constituent, current_id):
		constituent_id = row[indices['constituent_id_index']]
		type_key = int(row[indices['type_id_index']])
		type = CONSTITUENTTYPES.get(type_key)

		# could have multiple rows
		if constituent_id != current_id:
			save(constituent)
			current_id = constituent_id
			constituent = {}

		constituent['type'] = type
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

			if key in ['begindate', 'enddate']:
				if row_value == 0:
					row_value = None

			constituent[key] = row_value

		display_text = constituent['displayname']
		constituent['displaytext'] = display_text
		return (constituent, current_id)

	print("Starting Constituents...")
	print(datetime.now())
	if CURSOR:
		sql_command = constituents_sql.CONSTITUENTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		constituent = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			print("Going to process constituent row")
			print(datetime.now())
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			print("Finished processing constituent row")
			print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(constituent)

	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'constituents.csv'), 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)

	print("Finished Constituents...")
	print(datetime.now())


# Update relevant constituents with alternate names
def process_constituents_altnames(CURSOR):
	def get_indices():
		indices = {
			'constituent_id_index' : columns.index('ConstituentID'),
			'type_id_index' : columns.index('ConstituentTypeID'),
			'altname_index' : columns.index('DisplayName'),
			'name_type_index' : columns.index('NameType')
		}
		return indices

	def process_constituent_row(constituent, current_id):
		constituent_id = row[indices['constituent_id_index']]
		type_key = int(row[indices['type_id_index']])
		type = CONSTITUENTTYPES.get(type_key)

		if constituent_id != current_id:
			# will likely have multiple rows for one constituent because of many related objects
			# only get a new constituent if we have a new constituent id, but first save old constituent to elasticsearch
			save(constituent)
			current_id = constituent_id
			constituent = {}
			if elasticsearch_connection.item_exists(constituent_id, type, ELASTICSEARCH_INDEX):
				constituent = elasticsearch_connection.get_item(constituent_id, type, ELASTICSEARCH_INDEX)
			else:
				print("%s could not be found!" % constituent_id)
				return (constituent, current_id)

		if 'altnames' not in constituent:
			constituent['altnames'] = []
		altname = row[indices['altname_index']]
		name_type = row[indices['name_type_index']]
		constituent['altnames'].append({
			'name' : altname,
			'type' : name_type
		})
		return (constituent, current_id)

	print("Starting Constituents AltNames...")
	print(datetime.now())
	if CURSOR:
		sql_command = constituents_sql.ALT_NAMES
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		constituent = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			print("Going to process constituent altname row")
			print(datetime.now())
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			print("Finished processing constituent altname row")
			print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(constituent)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'constituents_altnames.csv'), 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)
	print("Finished Constituents AltNames...")
	print(datetime.now())

# Update all related items from the Objects table
def process_constituents_related_objects(CURSOR):
	def get_indices():
		indices = {
			'constituent_id_index' : columns.index('ConstituentID'),
			'type_id_index' : columns.index('ConstituentTypeID'),
			'object_id_index' : columns.index('ObjectID'),
			'object_title_index' : columns.index('Title'),
			'object_number_index' : columns.index('ObjectNumber'),
			'classification_id_index' : columns.index('ClassificationID'),
			'object_date_index' : columns.index('ObjectDate'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_constituent_row(constituent, current_id):
		constituent_id = row[indices['constituent_id_index']]
		type_key = int(row[indices['type_id_index']])
		type = CONSTITUENTTYPES.get(type_key)

		if constituent_id != current_id:
			# will likely have multiple rows for one constituent because of many related objects
			# only get a new constituent if we have a new constituent id, but first save old constituent to elasticsearch
			save(constituent)
			current_id = constituent_id
			constituent = {}
			if elasticsearch_connection.item_exists(constituent_id, type, ELASTICSEARCH_INDEX):
				constituent = elasticsearch_connection.get_item(constituent_id, type, ELASTICSEARCH_INDEX)
			else:
				print("%s could not be found!" % constituent_id)
				return (constituent, current_id)

		if 'relateditems' not in constituent:
			constituent['relateditems'] = {}
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)
		object_id = int(row[indices['object_id_index']])
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])

		date = "" if row[indices['object_date_index']].lower() == "null" else row[indices['object_date_index']]
		object_title = row[indices['object_title_index']]
		object_number = row[indices['object_number_index']]
		if classification == "diarypages" and object_title.lower() == "null":
			idx = object_number.find('_')
			object_title = object_number[idx+1:]
		if object_title.lower() == "null":
			object_title = "[No Title]"

		if classification not in constituent['relateditems']:
			constituent['relateditems'][classification] = []
		constituent['relateditems'][classification].append({
			'id' : object_id,
			'title' : object_title,
			'displaytext' : object_title,
			'classificationid' : classification_key,
			'number' : object_number,
			'date' : date,
			'thumbnail' : thumbnail_url})
		# keep the related items sorted
		constituent['relateditems'][classification].sort(key=operator.itemgetter('displaytext'))

		return (constituent, current_id)

	print("Starting Constituents Related Objects...")
	print(datetime.now())
	if CURSOR:
		sql_command = constituents_sql.RELATED_OBJECTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		constituent = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			print("Going to process constituent related object row")
			print(datetime.now())
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			print("Finished processing constituent related object row")
			print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(constituent)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'constituents_objects_related.csv'), 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)
	print("Finished Constituents Related Objects...")
	print(datetime.now())

# Next, update constituent with all related Sites
def process_constituents_related_sites(CURSOR):
	def get_indices():
		indices = {
			'constituent_id_index' : columns.index('ConstituentID'),
			'type_id_index' : columns.index('ConstituentTypeID'),
			'site_id_index' : columns.index('SiteID'),
			'site_name_index' : columns.index('SiteName'),
			'site_number_index' : columns.index('SiteNumber'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_constituent_row(constituent, current_id):
		constituent_id = row[indices['constituent_id_index']]
		type_key = int(row[indices['type_id_index']])
		type = CONSTITUENTTYPES.get(type_key)

		if constituent_id != current_id:
			# will likely have multiple rows for one constituent because of many related constituents
			# only get a new constituent if we have a new constituent id, but first save old constituent to elasticsearch
			save(constituent)
			current_id = constituent_id
			constituent = {}
			if elasticsearch_connection.item_exists(constituent_id, type, ELASTICSEARCH_INDEX):
				constituent = elasticsearch_connection.get_item(constituent_id, type, ELASTICSEARCH_INDEX)
			else:
				print("%s could not be found!" % constituent_id)
				return(constituent, current_id)
		if 'relateditems' not in constituent:
			constituent['relateditems'] = {}

		site_id = row[indices['site_id_index']]
		site_name = row[indices['site_name_index']]
		site_number = row[indices['site_number_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])

		site_dict = {}
		site_dict['id'] = site_id
		site_dict['sitename'] = site_name
		site_dict['sitenumber'] = site_number
		site_dict['displaytext'] = "%s, %s" % (site_name, site_number)
		site_dict['thumbnail'] = thumbnail_url

		if 'sites' not in constituent['relateditems']:
			constituent['relateditems']['sites'] = []
		constituent['relateditems']['sites'].append(site_dict)
		# keep the related items sorted
		constituent['relateditems']['sites'].sort(key=operator.itemgetter('displaytext'))

		return(constituent, current_id)

	print("Starting Constituents Related Sites...")
	print(datetime.now())
	if CURSOR:
		sql_command = constituents_sql.RELATED_SITES
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		constituent = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			print("Going to process constituent related site row")
			print(datetime.now())
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			print("Finished processing constituent related site row")
			print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(constituent)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'constituents_sites_related.csv'), 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)

	print("Finished Constituents Related Sites...")
	print(datetime.now())

# Next, update constituent with all related Published Documents
def process_constituents_related_published(CURSOR):
	def get_indices():
		indices = {
			'constituent_id_index' : columns.index('ConstituentID'),
			'type_id_index' : columns.index('ConstituentTypeID'),
			'reference_id_index' : columns.index('ReferenceID'),
			'title_index' : columns.index('Title'),
			'boiler_text_index' : columns.index('BoilerText'),
			'date_index' : columns.index('DisplayDate'),
			'path_index' : columns.index('MainPathName'),
			'file_index' : columns.index('MainFileName')
		}
		return indices

	def process_constituent_row(constituent, current_id):
		constituent_id = row[indices['constituent_id_index']]
		type_key = int(row[indices['type_id_index']])
		type = CONSTITUENTTYPES.get(type_key)

		if constituent_id != current_id:
			# will likely have multiple rows for one constituent because of many related published
			# only get a new constituent if we have a new constituent id, but first save old constituent to elasticsearch
			save(constituent)
			current_id = constituent_id
			constituent = {}
			if elasticsearch_connection.item_exists(constituent_id, type, ELASTICSEARCH_INDEX):
				constituent = elasticsearch_connection.get_item(constituent_id, type, ELASTICSEARCH_INDEX)
			else:
				print("%s could not be found!" % constituent_id)
				return(constituent, current_id)
		if 'relateditems' not in constituent:
			constituent['relateditems'] = {}

		reference_id = row[indices['reference_id_index']]
		title = row[indices['title_index']]
		boiler_text = row[indices['boiler_text_index']]
		date = "" if row[indices['date_index']].lower() == "null" else row[indices['date_index']]
		main_url = get_media_url(row[indices['path_index']], row[indices['file_index']])

		if "pubdocs" not in constituent['relateditems']:
			constituent['relateditems']["pubdocs"] = []
		constituent['relateditems']["pubdocs"].append({
			'id' : reference_id,
			'boilertext' : boiler_text,
			'displaytext' : title,
			'date' : date,
			'url' : main_url})
		# keep the related items sorted
		constituent['relateditems']['pubdocs'].sort(key=operator.itemgetter('displaytext'))
		return(constituent, current_id)

	print("Starting Constituents Related Published...")
	print(datetime.now())
	if CURSOR:
		sql_command = constituents_sql.RELATED_PUBLISHED
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		constituent = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			print("Going to process constituent related published row")
			print(datetime.now())
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			print("Finished processing constituent related published row")
			print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(constituent)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'constituents_published_related.csv'), 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)

	print("Finished Constituents Related Published...")
	print(datetime.now())

# Update constituent with all related media
def process_constituents_related_media(CURSOR):
	def get_indices():
		indices = {
			'constituent_id_index' : columns.index('ID'),
			'type_id_index' : columns.index('ConstituentTypeID'),
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

	def process_constituent_row(constituent, current_id):
		constituent_id = row[indices['constituent_id_index']]
		type_key = int(row[indices['type_id_index']])
		type = CONSTITUENTTYPES.get(type_key)

		if constituent_id != current_id:
			# will likely have multiple rows for one constituent because of many related photos
			# only get a new constituent if we have a new constituent id, but first save old constituent to elasticsearch
			save(constituent)
			current_id = constituent_id
			constituent = {}
			if elasticsearch_connection.item_exists(constituent_id, type, ELASTICSEARCH_INDEX):
				constituent = elasticsearch_connection.get_item(constituent_id, type, ELASTICSEARCH_INDEX)
			else:
				print("%s could not be found!" % constituent_id)
				return(constituent, current_id)
		if 'relateditems' not in constituent:
			constituent['relateditems'] = {}

		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)
		number = "" if row[indices['rendition_number_index']].lower() == "null" else row[indices['rendition_number_index']]
		media_master_id = row[indices['media_master_id_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])
		main_url = get_media_url(row[indices['main_path_index']], row[indices['main_file_index']])
		description = "" if row[indices['description_index']].lower() == "null" else row[indices['description_index']]
		mediaview = "" if row[indices['media_view_index']].lower() == "null" else row[indices['media_view_index']]
		caption = "" if row[indices['caption_index']].lower() == "null" else row[indices['caption_index']]
		display_text = ": ".join([mediaview, caption])
		drs_id = "" if row[indices['drs_id']].lower() == "null" else row[indices['drs_id']]
		primary_display = True if row[indices['primary_display_index']] == '1' else False

		# this is a bit of a hack because the MediaFormats for videos (in the TMS database) does not correctly identify the type of video
		# so, make sure we are only using videos that are mp4s
		if media_type_key == 3:
			if not row[indices['main_file_index']].endswith('mp4'):
				return(constituent, current_id)

		if media_type not in constituent['relateditems']:
			constituent['relateditems'][media_type] = []
		# add primary photo as a top level item as well
		if primary_display:
			constituent['primarydisplay'] = {
			'thumbnail' : thumbnail_url,
			'main' : main_url,
			'displaytext' : display_text,
			'number' : number,
			'description' : description,
			'drs_id' : drs_id
			}
		constituent['relateditems'][media_type].append({
			'id' : media_master_id,
			'displaytext' : display_text,
			'primarydisplay' : primary_display,
			'thumbnail' : thumbnail_url,
			'main' : main_url,
			'number' : number,
			'description' : description,
			'drs_id': drs_id
			})

		if drs_id != "":
			if drs_id not in ARCH_IDS.keys():
				manifest_ob = {
					"ArchIDNum": drs_id,
					"Description": description,
					"MediaView": mediaview
				}
				object = {
					"id": drs_id,
					"manifest": generate_iiif_manifest(manifest_ob)
				}
				save_manifest(object, drs_id)
				resource = object['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']
				ARCH_IDS[drs_id] = resource

			if constituent_id not in CONSTITUENT_RELATIONS.keys():
				CONSTITUENT_RELATIONS[constituent_id] = {
					'description': description,
					'label': mediaview,
					'resources': [
						ARCH_IDS[drs_id]
					],
					'type': type
				}
			else:
				CONSTITUENT_RELATIONS[constituent_id]['resources'].append(
					ARCH_IDS[drs_id]
				)
			if primary_display:
				CONSTITUENT_RELATIONS[constituent_id]['startCanvas'] = drs_id

		return(constituent, current_id)

	print("Starting Constituents Related Media...")
	print(datetime.now())
	if CURSOR:
		sql_command = constituents_sql.RELATED_MEDIA
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		constituent = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			print("Going to process constituent related media row")
			print(datetime.now())
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			print("Finished processing constituent related media row")
			print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(constituent)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'constituents_media_related.csv'), 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)

	print("Finished Constituents Related Media...")
	print(datetime.now())

# create manifests for all IIIF images per constituent
def compile_resources_by_constituent():
	print("Compiling associated constituent media for manifests.")
	for k, v in CONSTITUENT_RELATIONS.items():
		object = {
			"id": k,
			"manifest": generate_multi_canvas_iiif_manifest(k, v)
		}
		save_manifest(object, v['type'] + '-' + k)
	print(f"Compiled resources for {len(CONSTITUENT_RELATIONS)} constituents.")

def save(constituent):
	if constituent and 'id' in constituent:
		if not constituent['type']:
			print("%s is missing a type, ignoring for now" % (constituent['id']))
			return
		elasticsearch_connection.add_or_update_item(constituent['id'], json.dumps(constituent), constituent['type'], ELASTICSEARCH_INDEX)

def save_manifest(manifest, id):
	if manifest and 'id' in manifest:
		elasticsearch_connection.add_or_update_item(id, json.dumps(manifest), 'iiifmanifest', ELASTICSEARCH_INDEX)

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

	## process_constituents MUST go first.  The other methods can go in any order
	process_constituents(CURSOR)
	process_constituents_altnames(CURSOR)
	process_constituents_related_objects(CURSOR)
	process_constituents_related_sites(CURSOR)
	process_constituents_related_published(CURSOR)
	process_constituents_related_media(CURSOR)
	compile_resources_by_constituent()

if __name__ == "__main__":
	main()
