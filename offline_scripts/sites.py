

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
import sites_sql
from utils import get_media_url, process_cursor_row, generate_multi_canvas_iiif_manifest, create_thumbnail_url

ELASTICSEARCH_INDEX = 'giza'
ELASTICSEARCH_IIIF_INDEX = 'iiif'
SITE_RELATIONS = {}

DIRNAME = os.path.dirname(__file__)

#SAMPLE_SITES = ('1175', '670', '671', '672', '1509', '677', '2080', '2796', '2028', '2035', '2245', '2043', '3461', '3412')

# First update each Site with the latest data
# This is the basic information/metadata that comprises a Site
def process_sites(CURSOR):
	def get_indices():
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
	print(datetime.now())
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
			# print("Going to process site row")
			# print(datetime.now())
			(site, current_id) = process_site_row(site, current_id)
			# print("Finished processing site row")
			# print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)

	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'sites.csv'), 'r', encoding="utf-8-sig") as csvfile:
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
	print(datetime.now())

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
			if elasticsearch_connection.item_exists(site_id, 'sites', ELASTICSEARCH_INDEX):
				site = elasticsearch_connection.get_item(site_id, 'sites', ELASTICSEARCH_INDEX)
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
	print(datetime.now())
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
			# print("Going to process site dates row")
			# print(datetime.now())
			(site, current_id) = process_site_row(site, current_id)
			# print("Finished processing site dates row")
			# print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'sites_dates.csv'), 'r', encoding="utf-8-sig") as csvfile:
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
	print(datetime.now())

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
			if elasticsearch_connection.item_exists(site_id, 'sites', ELASTICSEARCH_INDEX):
				site = elasticsearch_connection.get_item(site_id, 'sites', ELASTICSEARCH_INDEX)
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
	print(datetime.now())
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
			# print("Going to process site altnums row")
			# print(datetime.now())
			(site, current_id) = process_site_row(site, current_id)
			# print("Finished processing site altnums row")
			# print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'sites_altnums.csv'), 'r', encoding="utf-8-sig") as csvfile:
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
	print(datetime.now())

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
			'thumb_file_index' : columns.index('ThumbFileName'),
			'drs_id' : columns.index('ArchIDNum')
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
			if elasticsearch_connection.item_exists(site_id, 'sites', ELASTICSEARCH_INDEX):
				site = elasticsearch_connection.get_item(site_id, 'sites', ELASTICSEARCH_INDEX)
			else:
				print("%s could not be found!" % site_id)
				return (site, current_id)

		if 'relateditems' not in site:
			site['relateditems'] = {}
		classification_key = int(row[indices['classification_id_index']])
		classification = CLASSIFICATIONS.get(classification_key)
		object_id = int(row[indices['object_id_index']])
		drs_id = "" if row[indices['drs_id']].lower() == "null" else row[indices['drs_id']]
		has_manifest = False if drs_id == "" else True
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])
		if not thumbnail_url and drs_id:
			thumbnail_url = create_thumbnail_url(drs_id)

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
			'thumbnail' : thumbnail_url,
			'has_manifest' : has_manifest})
		# keep the related items sorted
		site['relateditems'][classification].sort(key=operator.itemgetter('displaytext'))
		return (site, current_id)

	print("Starting Sites Related Objects...")
	print(datetime.now())
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
			# print("Going to process site related objects row")
			# print(datetime.now())
			(site, current_id) = process_site_row(site, current_id)
			# print("Finished processing site related objects row")
			# print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'sites_objects_related.csv'), 'r', encoding="utf-8-sig") as csvfile:
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
	print(datetime.now())

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
			'thumb_file_index' : columns.index('ThumbFileName'),
			'drs_id' : columns.index('ArchIDNum')
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
			if elasticsearch_connection.item_exists(site_id, 'sites', ELASTICSEARCH_INDEX):
				site = elasticsearch_connection.get_item(site_id, 'sites', ELASTICSEARCH_INDEX)
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
		drs_id = "" if row[indices['drs_id']].lower() == "null" else row[indices['drs_id']]
		has_manifest = False if drs_id == "" else True
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])
		if not thumbnail_url and drs_id:
			thumbnail_url = create_thumbnail_url(drs_id)

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
		constituent_dict['has_manifest'] = has_manifest

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
	print(datetime.now())
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
			# print("Going to process site related constituents row")
			# print(datetime.now())
			(site, current_id) = process_site_row(site, current_id)
			# print("Finished processing site related constituents row")
			# print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'sites_constituents_related.csv'), 'r', encoding="utf-8-sig") as csvfile:
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
	print(datetime.now())

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
			if elasticsearch_connection.item_exists(site_id, 'sites', ELASTICSEARCH_INDEX):
				site = elasticsearch_connection.get_item(site_id, 'sites', ELASTICSEARCH_INDEX)
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
			'displaytext' : boiler_text,
			'date' : date,
			'url' : main_url,
			'thumbnail' : thumbnail_url})
		# keep the related items sorted
		site['relateditems']['pubdocs'].sort(key=operator.itemgetter('displaytext'))
		return(site, current_id)

	print("Starting Sites Related Published...")
	print(datetime.now())
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
			# print("Going to process site related published row")
			# print(datetime.now())
			(site, current_id) = process_site_row(site, current_id)
			# print("Finished processing site related published row")
			# print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'sites_published_related.csv'), 'r', encoding="utf-8-sig") as csvfile:
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
	print(datetime.now())

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
			'main_file_index' : columns.index('MainFileName'),
			'drs_id' : columns.index('ArchIDNum')
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
			if elasticsearch_connection.item_exists(site_id, 'sites', ELASTICSEARCH_INDEX):
				site = elasticsearch_connection.get_item(site_id, 'sites', ELASTICSEARCH_INDEX)
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
		main_url = get_media_url(row[indices['main_path_index']], row[indices['main_file_index']])
		drs_id = "" if row[indices['drs_id']].lower() == "null" else row[indices['drs_id']]
		has_manifest = False if drs_id == "" else True
		primary_display = True if row[indices['primary_display_index']] == '1' else False
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])
		if not thumbnail_url and drs_id:
			thumbnail_url = create_thumbnail_url(drs_id)

		# this is a bit of a hack because the MediaFormats for videos (in the TMS database) does not correctly identify the type of video
		# so, make sure we are only using videos that are mp4s
		if media_type_key == 3:
			if not row[indices['main_file_index']].endswith('mp4'):
				return(site, current_id)

		if media_type not in site['relateditems']:
			site['relateditems'][media_type] = []
		# add primary photo as a top level item as well
		if primary_display:
			site['primarydisplay'] = {
			'thumbnail' : thumbnail_url,
			'main' : main_url,
			'displaytext' : display_text,
			'number' : number,
			'description' : description,
			'has_manifest' : has_manifest,
			'media_id' : media_master_id
			}
		site['relateditems'][media_type].append({
			'id' : media_master_id,
			'displaytext' : display_text,
			'primarydisplay' : primary_display,
			'thumbnail' : thumbnail_url,
			'main' : main_url,
			'number' : number,
			'description' : description,
			'has_manifest' : has_manifest,
			'drs_id' : drs_id
			})

		if has_manifest:
			object = elasticsearch_connection.get_item(media_type+'-'+media_master_id, 'manifest', ELASTICSEARCH_IIIF_INDEX)
			resource = object['manifest']['sequences'][0]['canvases'][0]['images'][0]['resource']
			canvas_label = object['manifest']['description']
			canvas_metadata = object['manifest']['metadata'] #add photo manifest-level metadata as canvas-level metadata for site

			if site_id not in SITE_RELATIONS.keys():
				metadata = add_metadata_to_manifest(site)

				SITE_RELATIONS[site_id] = {
					'description': site['description'],
					'label': site['displaytext'],
					'resources': [resource],
					'drs_ids' : [drs_id],
					'canvas_labels' : [canvas_label],
					'canvas_metadatas' : [canvas_metadata],
					'metadata' : metadata
				}
			else:
				SITE_RELATIONS[site_id]['resources'].append(resource)
				SITE_RELATIONS[site_id]['drs_ids'].append(drs_id)
				SITE_RELATIONS[site_id]['canvas_labels'].append(canvas_label)
				SITE_RELATIONS[site_id]['canvas_metadatas'].append(canvas_metadata)
			if primary_display:
				SITE_RELATIONS[site_id]['startCanvas'] = drs_id

		return(site, current_id)

	print("Starting Sites Related Media...")
	print(datetime.now())
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
			# print("Going to process site related media row")
			# print(datetime.now())
			(site, current_id) = process_site_row(site, current_id)
			# print("Finished processing site related media row")
			# print(datetime.now())
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(site)
	else:
		with open(os.path.join(DIRNAME, '..', 'data', 'sites_media_related.csv'), 'r', encoding="utf-8-sig") as csvfile:
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
	print(datetime.now())

# create manifests for all IIIF images per site
def compile_resources_by_site():
	print("Compiling associated site media for manifests.")
	for k, v in SITE_RELATIONS.items():
		manifest_id = 'sites-' + k
		object = {
			"id": manifest_id,
			"manifest": generate_multi_canvas_iiif_manifest(manifest_id, v)
		}
		save_manifest(object, manifest_id)
	print(f"Compiled resources for {len(SITE_RELATIONS)} sites.")

def save(site):
	if site and 'id' in site:
		elasticsearch_connection.add_or_update_item(site['id'], json.dumps(site), 'sites', ELASTICSEARCH_INDEX)

def save_manifest(manifest, id):
	if manifest and 'id' in manifest:
		elasticsearch_connection.add_or_update_item(id, json.dumps(manifest), 'manifest', ELASTICSEARCH_IIIF_INDEX)

def add_metadata_to_manifest(site):
	metadata = []
	for role in site['roles']:
		m = {}
		value = []
		m['label'] = role
		if 'modernpeople' in site['relateditems']:
			for item in site['relateditems']['modernpeople']:
				if item['role'] == role:
					v = item['displaytext']
					if item['displaydate']:
						v = v + ', ' + item['displaydate']
					value.append(v)
		if 'ancientpeople' in site['relateditems']:
			for item in site['relateditems']['ancientpeople']:
				if item['role'] == role:
					v = item['displaytext']
					if item['displaydate']:
						v = v + ', ' + item['displaydate']
					value.append(v)
		if 'institutions' in site['relateditems']:
			for item in site['relateditems']['institutions']:
				if item['role'] == role:
					v = item['displaytext']
					if item['displaydate']:
						v = v + ', ' + item['displaydate']
					value.append(v)
		if 'groups' in site['relateditems']:
			for item in site['relateditems']['groups']:
				if item['role'] == role:
					v = item['displaytext']
					if item['displaydate']:
						v = v + ', ' + item['displaydate']
					value.append(v)
		if 'animals' in site['relateditems']:
			for item in site['relateditems']['animals']:
				if item['role'] == role:
					v = item['displaytext']
					if item['displaydate']:
						v = v + ', ' + item['displaydate']
					value.append(v)
		m['value'] = value
		metadata.append(m)

	if 'altnum_types' in site:
		for altnumtype in site['altnum_types']:
			m = {}
			value = []
			m['label'] = altnumtype
			for altnum in site['altnums']:
				if altnum['description'] == altnumtype:
					value.append(altnum['altnum'])
			m['value'] = value
			metadata.append(m)

	if 'sitedates' in site:
		for sitedate in site['sitedates']:
			m = {}
			m['label'] = sitedate['type']
			m['value'] = sitedate['date']
			metadata.append(m)

	if 'sitetype' in site and 'sitetype' in site['sitetype']:
		m = {}
		m['label'] = 'Site Type'
		m['value'] = site['sitetype']['sitetype']
		metadata.append(m)

	if 'shafts' in site and site['shafts']:
		m = {}
		m['label'] = 'Shafts'
		m['value'] = site['shafts']
		metadata.append(m)

	if 'remarks' in site and site['remarks']:
		m = {}
		m['label'] = 'Remarks'
		m['value'] = site['remarks']
		metadata.append(m)

	if 'problemsquestions' in site and site['problemsquestions']:
		m = {}
		m['label'] = 'Problems/Questions'
		m['value'] = site['problemsquestions']
		metadata.append(m)
	return metadata

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

	## process_sites MUST go first.  The other methods can go in any order
	process_sites(CURSOR)
	process_site_dates(CURSOR)
	process_site_altnums(CURSOR)
	process_site_related_objects(CURSOR)
	process_site_related_constituents(CURSOR)
	process_site_related_published(CURSOR)
	process_site_related_media(CURSOR)
	compile_resources_by_site()

if __name__ == "__main__":
	main()
