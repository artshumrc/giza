import csv
import codecs
import elasticsearch_connection
import getpass
import json
import operator

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES, MEDIATYPES
import media_sql
from utils import get_media_url, process_cursor_row

# First update each Media with the latest data
# This is the basic information/metadata that comprises a Object
def process_media(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('MediaMasterID'),
			'rendition_number_index' : columns.index('RenditionNumber'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'description_index' : columns.index('Description'),
			'media_view_index' : columns.index('MediaView'),
			'caption_index' : columns.index('PublicCaption'),
			'remarks_index' : columns.index('Remarks'),
			'department_index' : columns.index('Department'),
			'date_index' : columns.index('DateOfCapture'),
			'problems_index' : columns.index('ProblemsQuestions'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName'),
			'main_path_index' : columns.index('MainPathName'),
			'main_file_index' : columns.index('MainFileName')
		}
		return indices

	def process_media_row(media, current_id):
		id = row[indices['id_index']]
		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)

		# for now, ignore Microfilm and Document media types
		if (media_type_key in [4,5]):
			return (media, current_id)

		if id != current_id:
			save(media)
			current_id = id
			media = {}

		media['id'] = id
		media['mediatype'] = media_type
		media['number'] = "" if row[indices['rendition_number_index']].lower() == "null" else row[indices['rendition_number_index']]
		media['description'] = "" if row[indices['description_index']].lower() == "null" else row[indices['description_index']]
		mediaview = "" if row[indices['media_view_index']].lower() == "null" else row[indices['media_view_index']]
		caption = "" if row[indices['caption_index']].lower() == "null" else row[indices['caption_index']]
		subjects = ": ".join([mediaview, caption])
		media['mediaview'] = mediaview
		media['subjects'] = subjects
		media['displaytext'] = subjects
		media['remarks'] = "" if row[indices['remarks_index']].lower() == "null" else row[indices['remarks_index']]
		media['department'] = "" if row[indices['department_index']].lower() == "null" else row[indices['department_index']]
		media['date'] = "" if row[indices['date_index']].lower() == "null" else row[indices['date_index']]
		media['problemsquestions'] = "" if row[indices['problems_index']].lower() == "null" else row[indices['problems_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])
		main_url = get_media_url(row[indices['main_path_index']], row[indices['main_file_index']])
		media['primarydisplay'] = {
		'thumbnail' : thumbnail_url,
		'main' : main_url
		}
		media['roles'] = []

		return (media, current_id)

	print "Starting Media..."
	if CURSOR:
		sql_command = media_sql.MEDIA
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		media = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(media, current_id) = process_media_row(media, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last media to elasticsearch
		save(media)

	else:
		with open('../data/media.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			media = {}
			current_id = '-1'
			for row in rows:
				(media, current_id) = process_media_row(media, current_id)
			# save last media to elasticsearch
			save(media)

	print "Finished Media..."

def process_media_related_sites(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('MediaMasterID'),
			'site_id_index' : columns.index('SiteID'),
			'site_name_index' : columns.index('SiteName'),
			'site_number_index' : columns.index('SiteNumber'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_media_row(media, current_id):
		id = row[indices['id_index']]
		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)

		# for now, ignore Microfilm and Document media types
		if (media_type_key in [4,5]):
			return (media, current_id)

		if id != current_id:
			save(media)
			current_id = id
			media = {}
			if elasticsearch_connection.item_exists(id, media_type):
				media = elasticsearch_connection.get_item(id, media_type)
			else:
				print "%s could not be found!" % id
				return(media, current_id)
		if 'relateditems' not in media:
			media['relateditems'] = {}

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

		if 'sites' not in media['relateditems']:
			media['relateditems']['sites'] = []
		media['relateditems']['sites'].append(site_dict)
		# keep the related items sorted
		media['relateditems']['sites'].sort(key=operator.itemgetter('displaytext'))

		return(media, current_id)

	print "Starting Media Related Sites..."
	if CURSOR:
		sql_command = media_sql.RELATED_SITES
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		media = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(media, current_id) = process_media_row(media, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last media to elasticsearch
		save(media)
	else:
		with open('../data/media_sites_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			media = {}
			current_id = '-1'
			for row in rows:
				(media, current_id) = process_media_row(media, current_id)
			# save last media to elasticsearch
			save(media)

	print "Finished Media Related Sites..."

# Update all related items from the Objects table
def process_media_related_objects(CURSOR):
	def get_indices():
		indices = {
			'media_id_index' : columns.index('MediaMasterID'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'object_id_index' : columns.index('ObjectID'),
			'object_title_index' : columns.index('Title'),
			'object_number_index' : columns.index('ObjectNumber'),
			'classification_id_index' : columns.index('ClassificationID'),
			'object_date_index' : columns.index('ObjectDate'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_media_row(media, current_id):
		id = row[indices['media_id_index']]
		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)

		# for now, ignore Microfilm and Document media types
		if (media_type_key in [4,5]):
			return (media, current_id)

		if id != current_id:
			save(media)
			current_id = id
			media = {}
			if elasticsearch_connection.item_exists(id, media_type):
				media = elasticsearch_connection.get_item(id, media_type)
			else:
				print "%s could not be found!" % id
				return (media, current_id)

		if 'relateditems' not in media:
			media['relateditems'] = {}
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

		if classification not in media['relateditems']:
			media['relateditems'][classification] = []
		media['relateditems'][classification].append({
			'id' : object_id,
			'title' : object_title,
			'displaytext' : object_title,
			'classificationid' : classification_key,
			'number' : object_number,
			'date' : date,
			'thumbnail' : thumbnail_url})
		# keep the related items sorted
		media['relateditems'][classification].sort(key=operator.itemgetter('displaytext'))

		return (media, current_id)

	print "Starting Media Related Objects..."
	if CURSOR:
		sql_command = media_sql.RELATED_OBJECTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		media = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(media, current_id) = process_media_row(media, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last object to elasticsearch
		save(media)
	else:
		with open('../data/media_objects_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			media = {}
			current_id = '-1'
			for row in rows:
				(media, current_id) = process_media_row(media, current_id)
			# save last object to elasticsearch
			save(media)
	print "Finished Media Related Objects..."

def process_media_related_constituents(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('MediaMasterID'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'role_index' : columns.index('Role'),
			'role_id_index' : columns.index('RoleID'),
			'constituent_id_index' : columns.index('ConstituentID'),
			'constituent_type_id_index' : columns.index('ConstituentTypeID'),
			'display_name_index' : columns.index('DisplayName'),
			'display_date_index' : columns.index('DisplayDate'),
			'remarks_index' : columns.index('Remarks'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_media_row(media, current_id):
		id = row[indices['id_index']]
		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)

		# for now, ignore Microfilm and Document media types
		if (media_type_key in [4,5]):
			return (media, current_id)

		if id != current_id:
			save(media)
			current_id = id
			media = {}
			if elasticsearch_connection.item_exists(id, media_type):
				media = elasticsearch_connection.get_item(id, media_type)
			else:
				print "%s could not be found!" % id
				return(media, current_id)
		if 'relateditems' not in media:
			media['relateditems'] = {}

		constituent_id = row[indices['constituent_id_index']]
		display_name = row[indices['display_name_index']]
		description = row[indices['remarks_index']] if row[indices['remarks_index']] != "NULL" else ""
		display_date = ""
		if row[indices['display_date_index']] != "NULL":
			display_date = row[indices['display_date_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])

		constituent_dict = {}
		role = row[indices['role_index']]
		# update the set of roles for this media
		if role not in media['roles']:
			# make sure Photographer is first
			if role == "Photographer":
				media['roles'].insert(0, role)
			else:
				media['roles'].append(role)

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
		if constituent_type not in media['relateditems']:
			media['relateditems'][constituent_type] = []
		media['relateditems'][constituent_type].append(constituent_dict)
		# keep the related items sorted
		media['relateditems'][constituent_type].sort(key=operator.itemgetter('displaytext'))

		return(media, current_id)

	print "Starting Media Related Constituents..."
	if CURSOR:
		# because this database can't be simple, we need to do two different queries to get related constituents
		for sql_command in [media_sql.RELATED_CONSTITUENTS_1, media_sql.RELATED_CONSTITUENTS_2]:
			CURSOR.execute(sql_command)
			columns = [column[0] for column in CURSOR.description]
			indices = get_indices()

			media = {}
			current_id = '-1'
			cursor_row = CURSOR.fetchone()
			while cursor_row is not None:
				row = process_cursor_row(cursor_row)
				(media, current_id) = process_media_row(media, current_id)
				cursor_row = CURSOR.fetchone()
	   		# save last media to elasticsearch
			save(media)
	else:
		with open('../data/media_constituents_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			media = {}
			current_id = '-1'
			for row in rows:
				(media, current_id) = process_media_row(media, current_id)
			# save last media to elasticsearch
			save(media)

	print "Finished Media Related Constituents..."

def process_media_related_published(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('MediaMasterID'),
			'media_type_id_index' : columns.index('MediaTypeID'),
			'reference_id_index' : columns.index('ReferenceID'),
			'title_index' : columns.index('Title'),
			'boiler_text_index' : columns.index('BoilerText'),
			'date_index' : columns.index('DisplayDate'),
			'path_index' : columns.index('MainPathName'),
			'file_index' : columns.index('MainFileName')
		}
		return indices

	def process_media_row(media, current_id):
		id = row[indices['id_index']]
		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)

		# for now, ignore Microfilm and Document media types
		if (media_type_key in [4,5]):
			return (media, current_id)

		if id != current_id:
			save(media)
			current_id = id
			media = {}
			if elasticsearch_connection.item_exists(id, media_type):
				media = elasticsearch_connection.get_item(id, media_type)
			else:
				print "%s could not be found!" % id
				return(media, current_id)
		if 'relateditems' not in media:
			media['relateditems'] = {}

		reference_id = row[indices['reference_id_index']]
		title = row[indices['title_index']]
		boiler_text = row[indices['boiler_text_index']]
		date = row[indices['date_index']]
		main_url = get_media_url(row[indices['path_index']], row[indices['file_index']])

		if 'pubdocs' not in media['relateditems']:
			media['relateditems']['pubdocs'] = []
		media['relateditems']['pubdocs'].append({
			'id' : reference_id,
			'boilertext' : boiler_text,
			'displaytext' : boiler_text,
			'date' : date,
			'url' : main_url})
		# keep the related items sorted
		media['relateditems']['pubdocs'].sort(key=operator.itemgetter('displaytext'))

		return(media, current_id)

	print "Starting Media Related Published..."
	if CURSOR:
		sql_command = media_sql.RELATED_PUBLISHED
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		media = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(media, current_id) = process_media_row(media, current_id)
			cursor_row = CURSOR.fetchone()
   		# save last media to elasticsearch
		save(media)
	else:
		with open('../data/media_published_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			media = {}
			current_id = '-1'
			for row in rows:
				(media, current_id) = process_media_row(media, current_id)
			# save last media to elasticsearch
			save(media)

	print "Finished Media Related Published..."

def save(media):
	if media and 'id' in media:
		if not media['mediatype']:
			# ignore for now, but this should send an email notification that there is missing data
			# so that the classifications.py file can be updated
			print "%s is missing a media type, ignoring for now" % (media['id'])
			return
		elasticsearch_connection.add_or_update_item(media['id'], json.dumps(media), media['mediatype'])

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

	## process_media MUST go first.  Other methods can go in any order
	process_media(CURSOR)
	process_media_related_sites(CURSOR)
	process_media_related_objects(CURSOR)
	process_media_related_constituents(CURSOR)
	process_media_related_published(CURSOR)

if __name__ == "__main__":
	main()
