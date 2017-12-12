import csv
import codecs
import elasticsearch_connection
import getpass
import json
import operator

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES, MEDIATYPES
import objects_sql
from utils import get_media_url, process_cursor_row

# SAMPLE_OBJECTS = ('61198', '15332', '15059', '52264', '50823', '35634', '5614', '46942', '48325', '3461', '25389', '25501')

# First update each Object with the latest data
# This is the basic information/metadata that comprises a Object
def process_objects(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('ID'),
			'classification_id_index' : columns.index('ClassificationID'),
			'object_number_index' : columns.index('Number')
		}
		return indices

	def process_object_row(object, current_id):
		id = row[indices['id_index']]
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)
		number = row[indices['object_number_index']]

		#if id not in SAMPLE_OBJECTS:
		#	return (object, current_id)

		# I don't think there are any duplicate rows for objects, but keep it here since it doesn't break anything
		if id != current_id:
			save(object)
			current_id = id
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
					idx = number.find('_')
					object_title = number[idx+1:]
					object[key] = object_title
				else:
					object[key] = row_value
			else:
				# remove whitespace at end of line if a string
				object[key] = row_value.rstrip() if type(row_value) is str else row_value
		# Add some extra fields not in the TMS data
		object['displaytext'] = object['title']
		prefix_idx = number.find('_')
		object['allnumbers'] = list(set([number, number[prefix_idx+1:], "".join(number.split())]))
		object['roles'] = []
		object['hasphoto'] = "No"
		return (object, current_id)

	print "Starting Objects..."
	if CURSOR:
		sql_command = objects_sql.OBJECTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(object, current_id) = process_object_row(object, current_id)
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
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(object, current_id)
			# save last object to elasticsearch
			save(object)

	print "Finished Objects..."

def process_object_geocodes(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('ID'),
			'geo_code_id_index' : columns.index('GeoCodeID'),
			'geo_code_index' : columns.index('GeoCode'),
			'region_index' : columns.index('Region'),
			'city_index' : columns.index('City'),
			'classification_id_index' : columns.index('ClassificationID')
		}
		return indices

	def process_object_row(object, current_id):
		id = row[indices['id_index']]
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)

		if id != current_id:
			# may have multiple rows for one object because of many related constituents
			save(object)
			current_id = id
			object = {}
			if elasticsearch_connection.item_exists(id, classification):
				object = elasticsearch_connection.get_item(id, classification)
			else:
				print "%s could not be found!" % id
				return(object, current_id)

		geocode_dict = {}
		geocode_dict['id'] = row[indices['geo_code_id_index']]
		geocode_dict['geocode'] = row[indices['geo_code_index']]
		geocode_dict['region'] = row[indices['region_index']]
		geocode_dict['city'] = row[indices['city_index']]
		object['geocode'] = geocode_dict

		return(object, current_id)

	print "Starting Objects Geocodes..."
	if CURSOR:
		sql_command = objects_sql.GEOCODES
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
	 	indices = get_indices()

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(object, current_id) = process_object_row(object, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(object)
	else:
		with open('../data/objects_geocodes.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(object, current_id)
			# save last object to elasticsearch
			save(object)

	print "Finished Objects Geocodes..."

# Update relevant objects with alternate numbers
def process_object_altnums(CURSOR):
	def get_indices():
		indices = {
			'object_id_index' : columns.index('ObjectID'),
			'classification_id_index' : columns.index('ClassificationID'),
			'altnum_index' : columns.index('AltNum'),
			'description_index' : columns.index('Description')
		}
		return indices

	def process_object_row(object, current_id):
		object_id = row[indices['object_id_index']]
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)

		if object_id != current_id:
			# will likely have multiple rows
			save(object)
			current_id = object_id
			object = {}
			if elasticsearch_connection.item_exists(object_id, classification):
				object = elasticsearch_connection.get_item(object_id, classification)
			else:
				print "%s could not be found!" % object_id
				return (object, current_id)

		if 'altnums' not in object:
			object['altnums'] = []
		altnum = row[indices['altnum_index']]
		prefix_idx = altnum.find('_')
		without_prefix = altnum[prefix_idx+1:]
		description = row[indices['description_index']] if row[indices['description_index']] != "NULL" else ""
		object['altnums'].append({"altnum" : altnum, "description" : description, 'without_prefix': without_prefix})
		object['allnumbers'].extend((altnum, without_prefix))
		return (object, current_id)

	print "Starting Objects AltNums..."
	if CURSOR:
		sql_command = objects_sql.ALTNUMS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(object, current_id) = process_object_row(object, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(object)
	else:
		with open('../data/objects_altnums.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(object, current_id)
			# save last object to elasticsearch
			save(object)
	print "Finished Objects AltNums..."

# Update relevant objects with alternate numbers
def process_object_flexfields(CURSOR):
	def get_indices():
		indices = {
			'object_id_index' : columns.index('ObjectID'),
			'classification_id_index' : columns.index('ClassificationID'),
			'group_name_index' : columns.index('GroupName'),
			'field_name_index' : columns.index('UserFieldName'),
			'field_value_index' : columns.index('FieldValue')
		}
		return indices

	def process_object_row(object, current_id):
		object_id = row[indices['object_id_index']]
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)

		if object_id != current_id:
			# will likely have multiple rows
			save(object)
			current_id = object_id
			object = {}
			if elasticsearch_connection.item_exists(object_id, classification):
				object = elasticsearch_connection.get_item(object_id, classification)
			else:
				print "%s could not be found!" % object_id
				return (object, current_id)

		if 'flexfields' not in object:
			object['flexfields'] = {}

		groupname = row[indices['group_name_index']]
		if groupname not in object['flexfields']:
			object['flexfields'][groupname] = []

		fieldname = row[indices['field_name_index']]
		fieldvalue = row[indices['field_value_index']]
		object['flexfields'][groupname].append({fieldname : fieldvalue})
		return (object, current_id)

	print "Starting Objects Flex Fields..."
	if CURSOR:
		sql_command = objects_sql.FLEXFIELDS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(object, current_id) = process_object_row(object, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(object)
	else:
		with open('../data/objects_flexfields.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(object, current_id)
			# save last object to elasticsearch
			save(object)
	print "Finished Objects Flex Fields..."

def process_object_related_sites(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('ID'),
			'site_id_index' : columns.index('SiteID'),
			'site_name_index' : columns.index('SiteName'),
			'site_number_index' : columns.index('SiteNumber'),
			'classification_id_index' : columns.index('ClassificationID'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_object_row(object, current_id):
		id = row[indices['id_index']]
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)

		if id != current_id:
			# may have multiple rows for one object because of many related constituents
			save(object)
			current_id = id
			object = {}
			if elasticsearch_connection.item_exists(id, classification):
				object = elasticsearch_connection.get_item(id, classification)
			else:
				print "%s could not be found!" % id
				return(object, current_id)
		if 'relateditems' not in object:
			object['relateditems'] = {}

		site_id = row[indices['site_id_index']]
		site_name = row[indices['site_name_index']]
		site_number = row[indices['site_number_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])

		site_dict = {}
		site_dict['id'] = site_id
		site_dict['sitename'] = site_name
		site_dict['sitenumber'] = site_number
		site_dict['displaytext'] = site_number
		site_dict['thumbnail'] = thumbnail_url

		if 'sites' not in object['relateditems']:
			object['relateditems']['sites'] = []
		object['relateditems']['sites'].append(site_dict)
		# keep the related items sorted
		object['relateditems']['sites'].sort(key=operator.itemgetter('displaytext'))

		# for unpubdocs, add sites for "Mentioned on this page"
		if classification == "unpubdocs":
			if 'mentioned' not in object:
				object['mentioned'] = {}
			if 'sites' not in object['mentioned']:
				object['mentioned']['sites'] = []
			object['mentioned']['sites'].append(site_dict)

		return(object, current_id)

	print "Starting Objects Related Sites..."
	if CURSOR:
		sql_command = objects_sql.RELATED_SITES
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(object, current_id) = process_object_row(object, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(object)
	else:
		with open('../data/objects_sites_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(object, current_id)
			# save last object to elasticsearch
			save(object)

	print "Finished Objects Related Sites..."

def process_object_related_constituents(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('ID'),
			'role_index' : columns.index('Role'),
			'role_id_index' : columns.index('RoleID'),
			'constituent_id_index' : columns.index('ConstituentID'),
			'constituent_type_id_index' : columns.index('ConstituentTypeID'),
			'display_name_index' : columns.index('DisplayName'),
			'display_date_index' : columns.index('DisplayDate'),
			'classification_id_index' : columns.index('ClassificationID'),
			'remarks_index' : columns.index('Remarks'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_object_row(object, current_id):
		id = row[indices['id_index']]
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)

		if id != current_id:
			# may have multiple rows for one object because of many related constituents
			save(object)
			current_id = id
			object = {}
			if elasticsearch_connection.item_exists(id, classification):
				object = elasticsearch_connection.get_item(id, classification)
			else:
				print "%s could not be found!" % id
				return(object, current_id)
		if 'relateditems' not in object:
			object['relateditems'] = {}

		constituent_id = row[indices['constituent_id_index']]
		display_name = row[indices['display_name_index']]
		description = row[indices['remarks_index']] if row[indices['remarks_index']] != "NULL" else ""
		display_date = ""
		if row[indices['display_date_index']] != "NULL":
			display_date = row[indices['display_date_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])

		constituent_dict = {}
		role = row[indices['role_index']]
		# update the set of roles for this object
		if role not in object['roles']:
			object['roles'].append(role)

		constituent_dict['role'] = row[indices['role_index']]
		constituent_dict['roleid'] = row[indices['role_id_index']]
		constituent_dict['id'] = constituent_id
		constituent_dict['displayname'] = display_name
		constituent_dict['displaydate'] = display_date
		constituent_dict['displaytext'] = display_name
		constituent_dict['description'] = description
		constituent_dict['thumbnail'] = thumbnail_url

		constituent_type_key = int(row[indices['constituent_type_id_index']])
		constituent_type = CONSTITUENTTYPES.get(constituent_type_key)
		if constituent_type not in object['relateditems']:
			object['relateditems'][constituent_type] = []
		object['relateditems'][constituent_type].append(constituent_dict)
		# keep the related items sorted
		object['relateditems'][constituent_type].sort(key=operator.itemgetter('displaytext'))

		return(object, current_id)

	print "Starting Objects Related Constituents..."
	if CURSOR:
		sql_command = objects_sql.RELATED_CONSTITUENTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(object, current_id) = process_object_row(object, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(object)
	else:
		with open('../data/objects_constituents_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(object, current_id)
			# save last object to elasticsearch
			save(object)

	print "Finished Objects Related Constituents..."

def process_object_related_published(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('ID'),
			'reference_id_index' : columns.index('ReferenceID'),
			'title_index' : columns.index('Title'),
			'boiler_text_index' : columns.index('BoilerText'),
			'classification_id_index' : columns.index('ClassificationID'),
			'date_index' : columns.index('DisplayDate'),
			'path_index' : columns.index('MainPathName'),
			'file_index' : columns.index('MainFileName')
		}
		return indices

	def process_object_row(object, current_id):
		id = row[indices['id_index']]
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)

		if id != current_id:
			# may have multiple rows for one object because of many related constituents
			save(object)
			current_id = id
			object = {}
			if elasticsearch_connection.item_exists(id, classification):
				object = elasticsearch_connection.get_item(id, classification)
			else:
				print "%s could not be found!" % id
				return(object, current_id)
		if 'relateditems' not in object:
			object['relateditems'] = {}

		reference_id = row[indices['reference_id_index']]
		title = row[indices['title_index']]
		boiler_text = row[indices['boiler_text_index']]
		date = row[indices['date_index']]
		main_url = get_media_url(row[indices['path_index']], row[indices['file_index']])

		if 'pubdocs' not in object['relateditems']:
			object['relateditems']['pubdocs'] = []
		object['relateditems']['pubdocs'].append({
			'id' : reference_id,
			'boilertext' : boiler_text,
			'displaytext' : boiler_text,
			'date' : date,
			'url' : main_url})
		# keep the related items sorted
		object['relateditems']['pubdocs'].sort(key=operator.itemgetter('displaytext'))

		return(object, current_id)

	print "Starting Objects Related Published..."
	if CURSOR:
		sql_command = objects_sql.RELATED_PUBLISHED
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(object, current_id) = process_object_row(object, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(object)
	else:
		with open('../data/objects_published_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(object, current_id)
			# save last object to elasticsearch
			save(object)

	print "Finished Objects Related Published..."

def process_object_related_unpublished(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('ID'),
			'unpublished_id_index' : columns.index('UnpublishedID'),
			'unpublished_title_index' : columns.index('UnpublishedTitle'),
			'classification_id_index' : columns.index('ClassificationID'),
			'object_date_index' : columns.index('ObjectDate'),
			'object_number_index' : columns.index('ObjectNumber'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_object_row(object, current_id):
		id = row[indices['id_index']]
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)

		if id != current_id:
			# may have multiple rows for one object because of many related constituents
			save(object)
			current_id = id
			object = {}
			if elasticsearch_connection.item_exists(id, classification):
				object = elasticsearch_connection.get_item(id, classification)
			else:
				print "%s could not be found!" % id
				return(object, current_id)
		if 'relateditems' not in object:
			object['relateditems'] = {}

		unpublished_id = row[indices['unpublished_id_index']]
		unpublished_title = row[indices['unpublished_title_index']]
		number = row[indices['object_number_index']]
		date = "" if row[indices['object_date_index']].lower() == "null" else row[indices['object_date_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])

		if 'unpubdocs' not in object['relateditems']:
			object['relateditems']['unpubdocs'] = []
		object['relateditems']['unpubdocs'].append({
			'id' : unpublished_id,
			'text' : unpublished_title,
			'displaytext' : unpublished_title,
			'date' : date,
			'number' : number,
			'thumbnail' : thumbnail_url})
		# keep the related items sorted
		object['relateditems']['unpubdocs'].sort(key=operator.itemgetter('displaytext'))

		return(object, current_id)

	print "Starting Objects Related Unpublished..."
	if CURSOR:
		sql_command = objects_sql.RELATED_UNPUBLISHED
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(object, current_id) = process_object_row(object, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(object)
	else:
		with open('../data/objects_unpublished_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(object, current_id)
			# save last object to elasticsearch
			save(object)

	print "Finished Objects Related Unpublished..."

def process_object_related_media(CURSOR):
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
			'main_file_index' : columns.index('MainFileName')
		}
		return indices

	def process_object_row(object, current_id):
		id = row[indices['id_index']]
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)

		if id != current_id:
			# may have multiple rows for one object because of many related constituents
			save(object)
			current_id = id
			object = {}
			if elasticsearch_connection.item_exists(id, classification):
				object = elasticsearch_connection.get_item(id, classification)
			else:
				print "%s could not be found!" % id
				return(object, current_id)
		if 'relateditems' not in object:
			object['relateditems'] = {}

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
		# this is a bit of a hack because the MediaFormats for videos (in the TMS database) does not correctly identify the type of video
		# so, make sure we are only using videos that are mp4s
		if media_type_key == 3:
			if not row[indices['main_file_index']].endswith('mp4'):
				return(object, current_id)

		if media_type not in object['relateditems']:
			object['relateditems'][media_type] = []

		if media_type == 'photos':
			object['hasphoto'] = "Yes"
		# add primary photo as a top level item as well
		if row[indices['primary_display_index']] == '1':
			object['primarydisplay'] = {
			'thumbnail' : thumbnail_url,
			'main' : main_url,
			'displaytext' : display_text,
			'number' : number,
			'description' : description
			}
		if not (classification == '3dmodels' and media_type == '3dmodels'):
			object['relateditems'][media_type].append({
				'id' : media_master_id,
				'displaytext' : display_text,
				'primarydisplay' : True if row[indices['primary_display_index']] == '1' else False,
				'thumbnail' : thumbnail_url,
				'main' : main_url,
				'number' : number,
				'description' : description
				})
		return(object, current_id)

	print "Starting Objects Related Media..."
	if CURSOR:
		sql_command = objects_sql.RELATED_MEDIA
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		object = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(object, current_id) = process_object_row(object, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(object)
	else:
		with open('../data/objects_media_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			object = {}
			current_id = '-1'
			for row in rows:
				(object, current_id) = process_object_row(object, current_id)
			# save last object to elasticsearch
			save(object)

	print "Finished Objects Related Media..."

def save(object):
	if object and 'id' in object:
		if not object['classification']:
			# ignore for now, but this should send an email notification that there is missing data
			# so that the classifications.py file can be updated
			print "%s is missing a classification, ignoring for now" % (object['id'])
			return
		elasticsearch_connection.add_or_update_item(object['id'], json.dumps(object), object['classification'])

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
			print "Could not connect to gizacardtms, defaulting to CSV files"

	## process_objects MUST go first.  Other methods can go in any order
	process_objects(CURSOR)
	#process_object_geocodes(CURSOR)
	process_object_altnums(CURSOR)
	process_object_flexfields(CURSOR)
	process_object_related_sites(CURSOR)
	process_object_related_constituents(CURSOR)
	process_object_related_published(CURSOR)
	process_object_related_unpublished(CURSOR)
	process_object_related_media(CURSOR)

if __name__ == "__main__":
	main()
