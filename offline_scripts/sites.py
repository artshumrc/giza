# eventually, this should be a live query from the SQL Server
# for now, use static files in the data/ directory

import csv
import codecs
import json
import elasticsearch_connection

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES

SAMPLE_SITES = ('1175', '670', '671', '672', '1509', '677', '2080', '2796', '2028', '2035', '2245', '2043', '3461', '3412')

# First update each Site with the latest data
# This is the basic information/metadata that comprises a Site
with open('../data/sites.csv', 'rb') as csvfile:
	# Get the query headers to use as keys in the JSON
	headers = next(csvfile)
	if headers.startswith(codecs.BOM_UTF8):
		headers = headers[3:]
	headers = headers.replace('\r\n','')
	columns = headers.split(',')
	site_id_index = columns.index('SiteID')

	objects = csv.reader(csvfile, delimiter=',', quotechar='"')

	site = {}
	current_id = '-1'
	for row in objects:
		site_id = row[site_id_index]
		if site_id not in SAMPLE_SITES:
			continue
		# could have multiple rows for one site because of multiple SiteDates or other pieces of information
		# only create a new site if we have a new site id, but first save old site to elasticsearch
		if site_id != current_id:
			if site:
				elasticsearch_connection.add_or_update_item(current_id, json.dumps(site), 'sites')
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
		#print json.dumps(site)
	if site:
		# save last site to elasticsearch
		elasticsearch_connection.add_or_update_item(current_id, json.dumps(site), 'sites')

# Update relevant sites with alternate numbers
with open('../data/sites_altnums.csv', 'rb') as csvfile:
	# Get the query headers to use as keys in the JSON
	headers = next(csvfile)
	if headers.startswith(codecs.BOM_UTF8):
		headers = headers[3:]
	headers = headers.replace('\r\n','')
	columns = headers.split(',')

	site_id_index = columns.index('SiteID')
	altnum_index = columns.index('AltNum')
	description_index = columns.index('Description')

	current_id = '-1'
	site = {}
	objects = csv.reader(csvfile, delimiter=',', quotechar='"')
	for row in objects:
		site_id = row[site_id_index]
		if site_id not in SAMPLE_SITES:
			continue
		
		if site_id != current_id:
			if site:
				# will likely have multiple rows for one site because of many related objects
				# only get a new site if we have a new site id, but first save old site to elasticsearch
				elasticsearch_connection.add_or_update_item(current_id, json.dumps(site), 'sites')
			current_id = site_id
			site = {}
			if elasticsearch_connection.item_exists(site_id, 'sites'):
				site = elasticsearch_connection.get_item(site_id, 'sites')
			else:
				print "this site could not be found!"
				continue

		if 'altnums' not in site:
			site['altnums'] = []
		altnum = row[altnum_index]
		description = row[description_index] if row[description_index] != "NULL" else ""
		site['altnums'].append({"altnum" : altnum, "description" : description})

# Update all related items from the Objects table
# TODO: Get Primary Image URL (need an image server first) 
with open('../data/sites_objects_related.csv', 'rb') as csvfile:
	# Get the query headers to use as keys in the JSON
	headers = next(csvfile)
	if headers.startswith(codecs.BOM_UTF8):
		headers = headers[3:]
	headers = headers.replace('\r\n','')
	columns = headers.split(',')

	site_id_index = columns.index('SiteID')
	classification_id_index = columns.index('ClassificationID')
	object_id_index = columns.index('ObjectID')
	object_title_index = columns.index('Title')
	object_number_index = columns.index('ObjectNumber')

	current_id = '-1'
	site = {}
	objects = csv.reader(csvfile, delimiter=',', quotechar='"')
	for row in objects:
		site_id = row[site_id_index]
		if site_id not in SAMPLE_SITES:
			continue
		if site_id != current_id:
			if site:
				# will likely have multiple rows for one site because of many related objects
				# only get a new site if we have a new site id, but first save old site to elasticsearch
				elasticsearch_connection.add_or_update_item(current_id, json.dumps(site), 'sites')
			current_id = site_id
			site = {}
			if elasticsearch_connection.item_exists(site_id, 'sites'):
				site = elasticsearch_connection.get_item(site_id, 'sites')
			else:
				print "this site could not be found!"
				continue
		if 'relateditems' not in site:
			site['relateditems'] = {}
		classification_key = int(row[classification_id_index])
		classification = CLASSIFICATIONS.get(classification_key)
		object_id = int(row[object_id_index])

		object_title = row[object_title_index]
		if classification == "diary pages" and object_title.lower() == "null":
			object_number = row[object_number_index]
			idx = object_number.find('_')
			object_title = object_number[idx+1:]
		if object_title.lower() == "null":
			object_title = "[No Title]"

		if classification not in site['relateditems']:
			site['relateditems'][classification] = []
		site['relateditems'][classification].append({'objectid' : object_id, 'title' : object_title, 'classificationid' : classification_key})
	if site:
		elasticsearch_connection.add_or_update_item(current_id, json.dumps(site), 'sites')

# Next, update site with all related Constituents
with open('../data/sites_constituents_related.csv', 'rb') as csvfile:
	# Get the query headers to use as keys in the JSON
	headers = next(csvfile)
	if headers.startswith(codecs.BOM_UTF8):
		headers = headers[3:]
	headers = headers.replace('\r\n','')
	columns = headers.split(',')

	site_id_index = columns.index('SiteID')
	role_index = columns.index('Role')
	constituent_id_index = columns.index('ConstituentID')
	constituent_type_id_index = columns.index('ConstituentTypeID')
	display_name_index = columns.index('DisplayName')
	display_date_index = columns.index('DisplayDate')

	current_id = '-1'
	site = {}
	objects = csv.reader(csvfile, delimiter=',', quotechar='"')
	for row in objects:
		site_id = row[site_id_index]
		if site_id not in SAMPLE_SITES:
			continue
		if site_id != current_id:
			if site:
				# will likely have multiple rows for one site because of many related constituents
				# only get a new site if we have a new site id, but first save old site to elasticsearch
				elasticsearch_connection.add_or_update_item(current_id, json.dumps(site), 'sites')
			current_id = site_id
			site = {}
			if elasticsearch_connection.item_exists(site_id, 'sites'):
				site = elasticsearch_connection.get_item(site_id, 'sites')
			else:
				print "this site could not be found!"
				continue
		if 'constituents' not in site:
			site['constituents'] = []			
		if 'relateditems' not in site:
			site['relateditems'] = {}

		constituent_id = row[constituent_id_index]
		display_name = row[display_name_index]

		constituent_dict = {}
		constituent_dict['role'] = row[role_index]
		constituent_dict['constituent_id'] = constituent_id
		constituent_dict['display_name'] =  display_name
		constituent_dict['display_date'] = row[display_date_index] if row[display_date_index] != "NULL" else ""
		site['constituents'].append(constituent_dict)

		constituent_type_key = int(row[constituent_type_id_index])
		constituent_type = CONSTITUENTTYPES.get(constituent_type_key)
		if constituent_type not in site['relateditems']:
			site['relateditems'][constituent_type] = []
		site['relateditems'][constituent_type].append({'constituentid' : constituent_id, 'displayname' : display_name, 'constituenttypeid' : constituent_type_key})
	if site:
		elasticsearch_connection.add_or_update_item(current_id, json.dumps(site), 'sites')
