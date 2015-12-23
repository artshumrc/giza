import csv
import codecs
import elasticsearch_connection
import getpass
import json
import pyodbc

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES
import sites_sql

#SAMPLE_SITES = ('1175', '670', '671', '672', '1509', '677', '2080', '2796', '2028', '2035', '2245', '2043', '3461', '3412')

CURSOR = None

# First update each Site with the latest data
# This is the basic information/metadata that comprises a Site
def process_sites():
	def get_indices():
		site_id_index = columns.index('SiteID')
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
				elif 'sitedates' in key:
					# there can be multiple sitedates
					# create an array that contains all sitedate objects
					if 'sitedates' not in site:
						site['sitedates'] = []
					# key looks like 'SiteDates_EventType_DateText'
					# row data looks like 'PorterMoss Date_Dynasty 5-6'
					# split on _ (and ignore first value in key)
					keys = key.split('_')[1:]
					if len(keys) > 2:
						print "too many items after splitting"
					values = row_value.split('_')
					if len(values) > 2:
						print "too many items after splitting"
					date = {}
					for i, k in enumerate(keys):
						if values[i]:
							date[k.lower()] = values[i]
					if date:
						site['sitedates'].append(date)
				else:
					# no special processing - just add it to the JSON
					site[key] = row_value
			return (site, current_id)

	print "Starting Sites..."
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
		with open('../data/sites.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			site_id_index = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)

	print "Finished Sites..."

# Update relevant sites with alternate numbers
def process_site_altnums():
	def get_indices():
		site_id_index = columns.index('SiteID')
		altnum_index = columns.index('AltNum')
		description_index = columns.index('Description')
		return (site_id_index, altnum_index, description_index)

	def process_site_row(site, current_id):
		site_id = row[site_id_index]
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
				print "%s could not be found!" % site_id
				return (site, current_id)

		if 'altnums' not in site:
			site['altnums'] = []
		altnum = row[altnum_index]
		description = row[description_index] if row[description_index] != "NULL" else ""
		site['altnums'].append({"altnum" : altnum, "description" : description})
		return (site, current_id)

	print "Starting Sites AltNums..."
	if CURSOR:
		sql_command = sites_sql.ALTNUMS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		(site_id_index, altnum_index, description_index) = get_indices()

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
		with open('../data/sites_altnums.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			(site_id_index, altnum_index, description_index) = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)
	print "Finished Sites AltNums..."

# Update all related items from the Objects table
# TODO: Get Primary Image URL (need an image server first)
def  process_site_related_objects():
	def get_indices():
		site_id_index = columns.index('SiteID')
		classification_id_index = columns.index('ClassificationID')
		object_id_index = columns.index('ObjectID')
		object_title_index = columns.index('Title')
		object_number_index = columns.index('ObjectNumber')
		return (site_id_index, classification_id_index, object_id_index, object_title_index, object_number_index)

	def process_site_row(site, current_id):
		site_id = row[site_id_index]
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
				print "%s could not be found!" % site_id
				return (site, current_id)
		
		if 'relateditems' not in site:
			site['relateditems'] = {}
		classification_key = int(row[classification_id_index])
		classification = CLASSIFICATIONS.get(classification_key)
		object_id = int(row[object_id_index])

		object_title = row[object_title_index]
		if classification == "diarypages" and object_title.lower() == "null":
			object_number = row[object_number_index]
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
			'classificationid' : classification_key})
		return (site, current_id)

	print "Starting Sites Related Objects..."
	if CURSOR:
		sql_command = sites_sql.RELATED_OBJECTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		(site_id_index, classification_id_index, object_id_index, object_title_index, object_number_index) = get_indices()

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
		with open('../data/sites_objects_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			(site_id_index, classification_id_index, object_id_index, object_title_index, object_number_index) = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)
	print "Finished Sites Related Objects..."

# Next, update site with all related Constituents
def process_site_related_constituents():
	def get_indices():
		site_id_index = columns.index('SiteID')
		role_index = columns.index('Role')
		constituent_id_index = columns.index('ConstituentID')
		constituent_type_id_index = columns.index('ConstituentTypeID')
		display_name_index = columns.index('DisplayName')
		display_date_index = columns.index('DisplayDate')
		return (site_id_index, role_index, constituent_id_index, constituent_type_id_index, display_name_index, display_date_index)

	def process_site_row(site, current_id):
		site_id = row[site_id_index]
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
				print "%s could not be found!" % site_id
				return(site, current_id)
		if 'relateditems' not in site:
			site['relateditems'] = {}

		constituent_id = row[constituent_id_index]
		display_name = row[display_name_index]
		display_date = ""
		if row[display_date_index] != "NULL":
			display_date = row[display_date_index]

		constituent_dict = {}
		constituent_dict['role'] = row[role_index]
		constituent_dict['id'] = constituent_id
		constituent_dict['displayname'] = display_name
		constituent_dict['displaydate'] = display_date
		constituent_dict['displaytext'] = display_name

		constituent_type_key = int(row[constituent_type_id_index])
		constituent_type = CONSTITUENTTYPES.get(constituent_type_key)
		if constituent_type not in site['relateditems']:
			site['relateditems'][constituent_type] = []
		site['relateditems'][constituent_type].append(constituent_dict)
		return(site, current_id)

	print "Starting Sites Related Constituents..."
	if CURSOR:
		sql_command = sites_sql.RELATED_CONSTITUENTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		(site_id_index, role_index, constituent_id_index, constituent_type_id_index, display_name_index, display_date_index) = get_indices()

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
		with open('../data/sites_constituents_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			(site_id_index, role_index, constituent_id_index, constituent_type_id_index, display_name_index, display_date_index) = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)

	print "Finished Sites Related Constituents..."

# Next, update site with all related Published Documents
def process_site_related_published():
	def get_indices():
		site_id_index = columns.index('SiteID')
		reference_id_index = columns.index('ReferenceID')
		boiler_text_index = columns.index('BoilerText')
		return (site_id_index, reference_id_index, boiler_text_index)
	
	def process_site_row(site, current_id):
		site_id = row[site_id_index]
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
				print "%s could not be found!" % site_id
				return(site, current_id)
		if 'relateditems' not in site:
			site['relateditems'] = {}

		reference_id = row[reference_id_index]
		boiler_text = row[boiler_text_index]

		if "publisheddocuments" not in site['relateditems']:
			site['relateditems']["publisheddocuments"] = []
		site['relateditems']["publisheddocuments"].append({
			'id' : reference_id, 
			'boilertext' : boiler_text,
			'displaytext' : boiler_text})
		return(site, current_id)

	print "Starting Sites Related Published..."
	if CURSOR:
		sql_command = sites_sql.RELATED_PUBLISHED
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		(site_id_index, reference_id_index, boiler_text_index) = get_indices()

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
		with open('../data/sites_published_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			(site_id_index, reference_id_index, boiler_text_index) = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)
	
	print "Finished Sites Related Published..."

# Update site with all related photos
def process_site_related_photos():
	def get_indices():
		site_id_index = columns.index('SiteID')
		media_master_id_index = columns.index('MediaMasterID')
		return (site_id_index, media_master_id_index)

	def process_site_row(site, current_id):
		site_id = row[site_id_index]
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
				print "%s could not be found!" % site_id
				return(site, current_id)		
		if 'relateditems' not in site:
			site['relateditems'] = {}

		media_master_id = row[media_master_id_index]
		if "photos" not in site['relateditems']:
			site['relateditems']["photos"] = []
		site['relateditems']["photos"].append({
			'id' : media_master_id,
			'displaytext' : media_master_id
			})
		return(site, current_id)

	print "Starting Sites Related Photos..."
	if CURSOR:
		sql_command = sites_sql.RELATED_MEDIA
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		(site_id_index, media_master_id_index) = get_indices()

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
		with open('../data/sites_photos_related.csv', 'rb') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			if headers.startswith(codecs.BOM_UTF8):
				headers = headers[3:]
			headers = headers.replace('\r\n','')
			columns = headers.split(',')
			(site_id_index, media_master_id_index) = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			site = {}
			current_id = '-1'
			for row in rows:
				(site, current_id) = process_site_row(site, current_id)
			# save last object to elasticsearch
			save(site)

	print "Finished Sites Related Photos..."

def process_cursor_row(cursor_row):
	row = []
	for x in cursor_row:
		if isinstance(x, int):
			row.append(str(x))
		elif isinstance(x, unicode):
			row.append(x.encode('utf-8'))
		else:
			row.append(str(x))
	return row

def save(site):
	if site:
		elasticsearch_connection.add_or_update_item(site['siteid'], json.dumps(site), 'sites')

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

	process_sites()
	process_site_altnums()
	process_site_related_objects()
	process_site_related_constituents()
	process_site_related_published()
	process_site_related_photos()