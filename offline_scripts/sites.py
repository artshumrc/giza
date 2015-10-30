# eventually, this should be a live query from the SQL Server
# for now, use static files in the data/ directory

import csv
import codecs
import json
import elasticsearch_connection

from classifications import CLASSIFICATIONS

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
		if site_id not in ('1','42','1175'):
			continue
		# could have multiple rows for one site because of multiple SiteDates or other pieces of information
		# only create a new site if we have a new site id
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
				values = row_value.split('_')
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
		elasticsearch_connection.add_or_update_item(current_id, json.dumps(site), 'sites')

# Then update all related items from the Objects table
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
		if site_id not in ('1','42','1175'):
			continue
		if site_id != current_id:
			if site:
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
		site['relateditems'][classification].append({'objectid' : object_id, 'title' : object_title})
	if site:
		elasticsearch_connection.add_or_update_item(current_id, json.dumps(site), 'sites')
