import csv
import codecs
import elasticsearch_connection
import getpass
import json

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES, MEDIATYPES
import constituents_sql
from utils import get_media_url, process_cursor_row

CURSOR = None

# First update each Constituent with the latest data
# This is the basic information/metadata that comprises a Constituent
def process_constituents():
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

	print "Starting Constituents..."
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
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(constituent)

	else:
		with open('../data/constituents.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)

	print "Finished Constituents..."

# Update relevant constituents with alternate names
def process_constituents_altnames():
	def get_indices():
		indices = {
			'constituent_id_index' : columns.index('ConstituentID'),
			'type_id_index' : columns.index('ConstituentTypeID'),
			'altname_index' : columns.index('DisplayName')
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
			if elasticsearch_connection.item_exists(constituent_id, type):
				constituent = elasticsearch_connection.get_item(constituent_id, type)
			else:
				print "%s could not be found!" % constituent_id
				return (constituent, current_id)

		if 'altnames' not in constituent:
			constituent['altnames'] = []
		altname = row[indices['altname_index']]
		constituent['altnames'].append(altname)
		return (constituent, current_id)

	print "Starting Constituents AltNames..."
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
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(constituent)
	else:
		with open('../data/constituents_altnames.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)
	print "Finished Constituents AltNames..."

# Update all related items from the Objects table
def process_constituents_related_objects():
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
			if elasticsearch_connection.item_exists(constituent_id, type):
				constituent = elasticsearch_connection.get_item(constituent_id, type)
			else:
				print "%s could not be found!" % constituent_id
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
		return (constituent, current_id)

	print "Starting Constituents Related Objects..."
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
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(constituent)
	else:
		with open('../data/constituents_objects_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)
	print "Finished Constituents Related Objects..."

# Next, update constituent with all related Sites
def process_constituents_related_sites():
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
			if elasticsearch_connection.item_exists(constituent_id, type):
				constituent = elasticsearch_connection.get_item(constituent_id, type)
			else:
				print "%s could not be found!" % constituent_id
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
		return(constituent, current_id)

	print "Starting Constituents Related Sites..."
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
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(constituent)
	else:
		with open('../data/constituents_sites_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)

	print "Finished Constituents Related Sites..."

# Next, update constituent with all related Published Documents
def process_constituents_related_published():
	def get_indices():
		indices = {
			'constituent_id_index' : columns.index('ID'),
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
			if elasticsearch_connection.item_exists(constituent_id, type):
				constituent = elasticsearch_connection.get_item(constituent_id, type)
			else:
				print "%s could not be found!" % constituent_id
				return(constituent, current_id)
		if 'relateditems' not in constituent:
			constituent['relateditems'] = {}

		reference_id = row[indices['reference_id_index']]
		title = row[indices['title_index']]
		boiler_text = row[indices['boiler_text_index']]
		date = row[indices['date_index']]
		main_url = get_media_url(row[indices['path_index']], row[indices['file_index']])

		if "pubdocs" not in constituent['relateditems']:
			constituent['relateditems']["pubdocs"] = []
		constituent['relateditems']["pubdocs"].append({
			'id' : reference_id,
			'boilertext' : boiler_text,
			'displaytext' : title,
			'date' : date,
			'url' : main_url})
		return(constituent, current_id)

	print "Starting Constituents Related Published..."
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
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(constituent)
	else:
		with open('../data/constituents_published_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)

	print "Finished Constituents Related Published..."

# Update constituent with all related media
def process_constituents_related_media():
	def get_indices():
		indices = {
			'constituent_id_index' : columns.index('ID'),
			'type_id_index' : columns.index('ConstituentTypeID'),
			'media_master_id_index' : columns.index('MediaMasterID'),
			'primary_display_index' : columns.index('PrimaryDisplay'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'description_index' : columns.index('Description'),
			'caption_index' : columns.index('PublicCaption'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName'),
			'main_path_index' : columns.index('MainPathName'),
			'main_file_index' : columns.index('MainFileName')
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
			if elasticsearch_connection.item_exists(constituent_id, type):
				constituent = elasticsearch_connection.get_item(constituent_id, type)
			else:
				print "%s could not be found!" % constituent_id
				return(constituent, current_id)
		if 'relateditems' not in constituent:
			constituent['relateditems'] = {}

		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)
		media_master_id = row[indices['media_master_id_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])
		main_url = get_media_url(row[indices['main_path_index']], row[indices['main_file_index']])
		display_text = row[indices['caption_index']]

		# this is a bit of a hack because the MediaFormats for videos (in the TMS database) does not correctly identify the type of video
		# so, make sure we are only using videos that are mp4s
		if media_type_key == 3:
			if not row[indices['main_file_index']].endswith('mp4'):
				return(constituent, current_id)

		if media_type not in constituent['relateditems']:
			constituent['relateditems'][media_type] = []
		# add primary photo as a top level item as well
		if row[indices['primary_display_index']] == '1':
			constituent['primarydisplay'] = {
			'thumbnail' : thumbnail_url,
			'main' : main_url,
			'displaytext' : display_text
			}
		constituent['relateditems'][media_type].append({
			'id' : media_master_id,
			'displaytext' : display_text,
			'primarydisplay' : True if row[indices['primary_display_index']] == '1' else False,
			'thumbnail' : thumbnail_url,
			'main' : main_url
			})
		return(constituent, current_id)

	print "Starting Constituents Related Media..."
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
			(constituent, current_id) = process_constituent_row(constituent, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(constituent)
	else:
		with open('../data/constituents_media_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			constituent = {}
			current_id = '-1'
			for row in rows:
				(constituent, current_id) = process_constituent_row(constituent, current_id)
			# save last object to elasticsearch
			save(constituent)

	print "Finished Constituents Related Media..."

def save(constituent):
	if constituent and 'id' in constituent:
		if not constituent['type']:
			print "%s is missing a type, ignoring for now" % (constituent['id'])
			return
		elasticsearch_connection.add_or_update_item(constituent['id'], json.dumps(constituent), constituent['type'])

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
		print "Could not connect to gizacardtms, defaulting to CSV files"

	## process_constituents MUST go first.  The other methods can go in any order
	process_constituents()
	process_constituents_altnames()
	process_constituents_related_objects()
	process_constituents_related_sites()
	process_constituents_related_published()
	process_constituents_related_media()
