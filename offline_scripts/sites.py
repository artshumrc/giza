from __future__ import print_function
from __future__ import unicode_literals
from builtins import next
import csv
import codecs
import elasticsearch_connection
import getpass
import json
import operator

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES, MEDIATYPES
import sites_sql
from utils import get_media_url, process_cursor_row

#SAMPLE_SITES = ('1175', '670', '671', '672', '1509', '677', '2080', '2796', '2028', '2035', '2245', '2043', '3461', '3412')

# First update each Site with the latest data
# This is the basic information/metadata that comprises a Site
def process_sites(CURSOR):
	def get_indices():
		print(columns)
		site_id_index = columns.index('ID')
		return site_id_index

	def process_site_row(site, current_id):
		site_id = row[site_id_index]
		#if site_id not in SAMPLE_SITES:
		#	continue
		# could have multiple rows for one site because of multiple SiteDates or other pieces of information
		# only create a new site if we have a new site id, but first save old site to elasticsearch
		if site_id != current_id:
			save(site)
			current_id = site_id
			site = {}

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

			if 'sitetype' in key:
				if not row_value:
					continue
				# group sitetype fields into an object
				if 'sitetype' not in site:
					site['sitetype'] = {}
				site['sitetype'][key] = row_value
			else:
				# no special processing - just add it to the JSON
				site[key] = row_value
		number = site['number']
		prefix_idx = number.find('_')
		site['allnumbers'] = list(set([number, number[prefix_idx+1:], "".join(number.split())]))
		site['displaytext'] = number
		site['tombowner'] = "No"
		site['roles'] = []
		site['people'] = []
		site['datevalues'] = []
		return (site, current_id)

	print("Starting Sites...")
	if CURSOR:
		sql_command = sites_sql.SITES
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		site_id_index = get_indices()

		site = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(site, current_id) = process_site_row(site, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)

	else:
		with open('../data/sites.csv', 'r', encoding="utf-8-sig") as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n','')
			columns = headers.split(',')
			site_id_index = get_indices()

			rows = csv.reader(csvfile, delimiter=",", quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)

	print("Finished Sites...")

def process_site_dates(CURSOR):
	def get_indices():
		indices = {
			'site_id_index' : columns.index('SiteID'),
			'event_type_index' : columns.index('EventType'),
			'date_text_index' : columns.index('DateText')
		}
		return indices

	def process_site_row(site, current_id):
		site_id = row[indices['site_id_index']]

		if site_id != current_id:
			# will likely have multiple rows for one site because of many related objects
			# only get a new site if we have a new site id, but first save old site to elasticsearch
			save(site)
			current_id = site_id
			site = {}
			if elasticsearch_connection.item_exists(site_id, 'sites'):
				site = elasticsearch_connection.get_item(site_id, 'sites')
			else:
				print("%s could not be found!" % site_id)
				return (site, current_id)

		if 'sitedates' not in site:
			site['sitedates'] = []

		event_type = row[indices['event_type_index']]
		date_text = row[indices['date_text_index']]

		site['sitedates'].append({
			'type' : event_type,
			'date' : date_text
		})
		site['datevalues'].append(date_text)
		return (site, current_id)

	print("Starting Sites Dates...")
	if CURSOR:
		sql_command = sites_sql.SITEDATES
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		site = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(site, current_id) = process_site_row(site, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open('../data/sites_dates.csv', 'r', encoding="utf-8-sig") as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)
	print("Finished Sites Dates...")

# Update relevant sites with alternate numbers
def process_site_altnums(CURSOR):
	def get_indices():
		indices = {
			'site_id_index' : columns.index('SiteID'),
			'altnum_index' : columns.index('AltNum'),
			'description_index' : columns.index('Description')
		}
		return indices

	def process_site_row(site, current_id):
		site_id = row[indices['site_id_index']]
		#if site_id not in SAMPLE_SITES:
		#	continue

		if site_id != current_id:
			# will likely have multiple rows for one site because of many related objects
			# only get a new site if we have a new site id, but first save old site to elasticsearch
			save(site)
			current_id = site_id
			site = {}
			if elasticsearch_connection.item_exists(site_id, 'sites'):
				site = elasticsearch_connection.get_item(site_id, 'sites')
			else:
				print("%s could not be found!" % site_id)
				return (site, current_id)

		if 'altnums' not in site:
			site['altnums'] = []
		if 'altnum_types' not in site:
			site['altnum_types'] = []

		altnum = row[indices['altnum_index']]
		description = row[indices['description_index']] if row[indices['description_index']] != "NULL" else ""
		if description not in site['altnum_types']:
			site['altnum_types'].append(description)

		site['altnums'].append({"altnum" : altnum, "description" : description})
		return (site, current_id)

	print("Starting Sites AltNums...")
	if CURSOR:
		sql_command = sites_sql.ALTNUMS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		site = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(site, current_id) = process_site_row(site, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open('../data/sites_altnums.csv', 'r', encoding="utf-8-sig") as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)
	print("Finished Sites AltNums...")

# Update all related items from the Objects table
def process_site_related_objects(CURSOR):
	def get_indices():
		indices = {
			'site_id_index' : columns.index('SiteID'),
			'classification_id_index' : columns.index('ClassificationID'),
			'object_id_index' : columns.index('ObjectID'),
			'object_title_index' : columns.index('Title'),
			'object_number_index' : columns.index('ObjectNumber'),
			'object_date_index' : columns.index('ObjectDate'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_site_row(site, current_id):
		site_id = row[indices['site_id_index']]
		#if site_id not in SAMPLE_SITES:
		#	continue
		if site_id != current_id:
			# will likely have multiple rows for one site because of many related objects
			# only get a new site if we have a new site id, but first save old site to elasticsearch
			save(site)
			current_id = site_id
			site = {}
			if elasticsearch_connection.item_exists(site_id, 'sites'):
				site = elasticsearch_connection.get_item(site_id, 'sites')
			else:
				print("%s could not be found!" % site_id)
				return (site, current_id)

		if 'relateditems' not in site:
			site['relateditems'] = {}
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

		if classification not in site['relateditems']:
			site['relateditems'][classification] = []
		site['relateditems'][classification].append({
			'id' : object_id,
			'title' : object_title,
			'displaytext' : object_title,
			'classificationid' : classification_key,
			'number' : object_number,
			'date' : date,
			'thumbnail' : thumbnail_url})
		# keep the related items sorted
		site['relateditems'][classification].sort(key=operator.itemgetter('displaytext'))
		return (site, current_id)

	print("Starting Sites Related Objects...")
	if CURSOR:
		sql_command = sites_sql.RELATED_OBJECTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		site = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(site, current_id) = process_site_row(site, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open('../data/sites_objects_related.csv', 'r', encoding="utf-8-sig") as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)
	print("Finished Sites Related Objects...")

# Next, update site with all related Constituents
def process_site_related_constituents(CURSOR):
	def get_indices():
		indices = {
			'site_id_index' : columns.index('SiteID'),
			'role_index' : columns.index('Role'),
			'constituent_id_index' : columns.index('ConstituentID'),
			'constituent_type_id_index' : columns.index('ConstituentTypeID'),
			'display_name_index' : columns.index('DisplayName'),
			'display_date_index' : columns.index('DisplayDate'),
			'remarks_index' : columns.index('Remarks'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_site_row(site, current_id):
		site_id = row[indices['site_id_index']]
		#if site_id not in SAMPLE_SITES:
		#	continue
		if site_id != current_id:
			# will likely have multiple rows for one site because of many related constituents
			# only get a new site if we have a new site id, but first save old site to elasticsearch
			save(site)
			current_id = site_id
			site = {}
			if elasticsearch_connection.item_exists(site_id, 'sites'):
				site = elasticsearch_connection.get_item(site_id, 'sites')
			else:
				print("%s could not be found!" % site_id)
				return(site, current_id)
		if 'relateditems' not in site:
			site['relateditems'] = {}

		constituent_id = row[indices['constituent_id_index']]
		display_name = row[indices['display_name_index']]
		display_date = ""
		if row[indices['display_date_index']] != "NULL":
			display_date = row[indices['display_date_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])

		constituent_dict = {}
		role = row[indices['role_index']]
		# update the set of roles for this site
		if role not in site['roles']:
			# make sure Tomb Owner is first
			if role == "Tomb Owner":
				site['roles'].insert(0, role)
			else:
				site['roles'].append(role)

		description = row[indices['remarks_index']] if row[indices['remarks_index']] != "NULL" else ""
		constituent_dict['role'] = role
		constituent_dict['id'] = constituent_id
		constituent_dict['displayname'] = display_name
		constituent_dict['displaydate'] = display_date
		constituent_dict['displaytext'] = display_name
		constituent_dict['description'] = description
		constituent_dict['thumbnail'] = thumbnail_url

		constituent_type_key = int(row[indices['constituent_type_id_index']])
		constituent_type = CONSTITUENTTYPES.get(constituent_type_key)

		# add to array of people for easier searching
		if (constituent_type_key in [1,3]):
			site['people'].append(display_name)

		if constituent_type not in site['relateditems']:
			site['relateditems'][constituent_type] = []
		site['relateditems'][constituent_type].append(constituent_dict)
		# keep the related items sorted
		site['relateditems'][constituent_type].sort(key=operator.itemgetter('displaytext'))

		if role == 'Tomb Owner':
			site['tombowner'] = "Yes"
		return(site, current_id)

	print("Starting Sites Related Constituents...")
	if CURSOR:
		sql_command = sites_sql.RELATED_CONSTITUENTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		site = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(site, current_id) = process_site_row(site, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open('../data/sites_constituents_related.csv', 'r', encoding="utf-8-sig") as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)

	print("Finished Sites Related Constituents...")

# Next, update site with all related Published Documents
def process_site_related_published(CURSOR):
	def get_indices():
		indices = {
			'site_id_index' : columns.index('SiteID'),
			'reference_id_index' : columns.index('ReferenceID'),
			'title_index' : columns.index('Title'),
			'boiler_text_index' : columns.index('BoilerText'),
			'date_index' : columns.index('DisplayDate'),
			'path_index' : columns.index('MainPathName'),
			'file_index' : columns.index('MainFileName'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')		}
		return indices

	def process_site_row(site, current_id):
		site_id = row[indices['site_id_index']]
		#if site_id not in SAMPLE_SITES:
		#	continue
		if site_id != current_id:
			# will likely have multiple rows for one site because of many related published
			# only get a new site if we have a new site id, but first save old site to elasticsearch
			save(site)
			current_id = site_id
			site = {}
			if elasticsearch_connection.item_exists(site_id, 'sites'):
				site = elasticsearch_connection.get_item(site_id, 'sites')
			else:
				print("%s could not be found!" % site_id)
				return(site, current_id)
		if 'relateditems' not in site:
			site['relateditems'] = {}

		reference_id = row[indices['reference_id_index']]
		title = row[indices['title_index']]
		boiler_text = row[indices['boiler_text_index']]
		date = row[indices['date_index']]
		main_url = get_media_url(row[indices['path_index']], row[indices['file_index']])
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])

		if "pubdocs" not in site['relateditems']:
			site['relateditems']["pubdocs"] = []
		site['relateditems']["pubdocs"].append({
			'id' : reference_id,
			'boilertext' : boiler_text,
			'displaytext' : title,
			'date' : date,
			'url' : main_url,
			'thumbnail' : thumbnail_url})
		# keep the related items sorted
		site['relateditems']['pubdocs'].sort(key=operator.itemgetter('displaytext'))
		return(site, current_id)

	print("Starting Sites Related Published...")
	if CURSOR:
		sql_command = sites_sql.RELATED_PUBLISHED
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		site = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(site, current_id) = process_site_row(site, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open('../data/sites_published_related.csv', 'r', encoding="utf-8-sig") as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)

	print("Finished Sites Related Published...")

# Update site with all related media
def process_site_related_media(CURSOR):
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
			'main_file_index' : columns.index('MainFileName')
		}
		return indices

	def process_site_row(site, current_id):
		site_id = row[indices['site_id_index']]
		#if site_id not in SAMPLE_SITES:
		#	continue
		if site_id != current_id:
			# will likely have multiple rows for one site because of many related photos
			# only get a new site if we have a new site id, but first save old site to elasticsearch
			save(site)
			current_id = site_id
			site = {}
			if elasticsearch_connection.item_exists(site_id, 'sites'):
				site = elasticsearch_connection.get_item(site_id, 'sites')
			else:
				print("%s could not be found!" % site_id)
				return(site, current_id)
		if 'relateditems' not in site:
			site['relateditems'] = {}

		media_type_key = int(row[indices['media_type_id_index']])
		media_type = MEDIATYPES.get(media_type_key)
		number = "" if row[indices['rendition_number_index']].lower() == "null" else row[indices['rendition_number_index']]
		description = "" if row[indices['description_index']].lower() == "null" else row[indices['description_index']]
		mediaview = "" if row[indices['media_view_index']].lower() == "null" else row[indices['media_view_index']]
		caption = "" if row[indices['caption_index']].lower() == "null" else row[indices['caption_index']]
		display_text = ": ".join([mediaview, caption])
		media_master_id = row[indices['media_master_id_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])
		main_url = get_media_url(row[indices['main_path_index']], row[indices['main_file_index']])

		# this is a bit of a hack because the MediaFormats for videos (in the TMS database) does not correctly identify the type of video
		# so, make sure we are only using videos that are mp4s
		if media_type_key == 3:
			if not row[indices['main_file_index']].endswith('mp4'):
				return(site, current_id)

		if media_type not in site['relateditems']:
			site['relateditems'][media_type] = []
		# add primary photo as a top level item as well
		if row[indices['primary_display_index']] == '1':
			site['primarydisplay'] = {
			'thumbnail' : thumbnail_url,
			'main' : main_url,
			'displaytext' : display_text,
			'number' : number,
			'description' : description
			}
		site['relateditems'][media_type].append({
			'id' : media_master_id,
			'displaytext' : display_text,
			'primarydisplay' : True if row[indices['primary_display_index']] == '1' else False,
			'thumbnail' : thumbnail_url,
			'main' : main_url,
			'number' : number,
			'description' : description
			})
		return(site, current_id)

	print("Starting Sites Related Media...")
	if CURSOR:
		sql_command = sites_sql.RELATED_MEDIA
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		site = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(site, current_id) = process_site_row(site, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open('../data/sites_media_related.csv', 'r', encoding="utf-8-sig") as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n','')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)

	print("Finished Sites Related Media...")

def save(site):
	if site and 'id' in site:
		elasticsearch_connection.add_or_update_item(site['id'], json.dumps(site), 'sites')

def main(CURSOR=None):
	# if not CURSOR:
	# 	try:
	# 		import pyodbc
	# 		dsn = 'gizadatasource'
	# 		user = 'RC\\rsinghal'
	# 		password = getpass.getpass()
	# 		database = 'gizacardtms'

	# 		connection_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, user, password, database)
	# 		connection = pyodbc.connect(connection_string)
	# 		CURSOR = connection.cursor()
	# 	except:
	# 		print "Could not connect to gizacardtms, defaulting to CSV files"

	## process_sites MUST go first.  The other methods can go in any order
	process_sites(CURSOR)
	process_site_dates(CURSOR)
	process_site_altnums(CURSOR)
	process_site_related_objects(CURSOR)
	process_site_related_constituents(CURSOR)
	process_site_related_published(CURSOR)
	process_site_related_media(CURSOR)

if __name__ == "__main__":
	main()
