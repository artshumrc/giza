# eventually, this should be a live query from the SQL Server
# for now, use static files in the data/ directory

import csv
import codecs
import json
from classifications import CLASSIFICATIONS

with open('../data/sites.csv', 'rb') as csvfile:
	headers = next(csvfile)
	if headers.startswith(codecs.BOM_UTF8):
		headers = headers[3:]
	headers = headers.replace('\r\n','')
	columns = headers.split(',')
	print columns
	objects = csv.reader(csvfile, delimiter=',', quotechar='"')

	site = {}
	current_id = '-1'
	for row in objects:
		if row[0] not in ('1','42'):
			continue
		print row[0]
		if row[0] != current_id:
			current_id = row[0]
			site = {}

		# could have multiple rows for one site because of multiple SiteDates or other pieces of information
		for index, value in enumerate(columns):
			key = value.lower()
			if 'sitetype' in key:
				if 'sitetype' not in site:
					site['sitetype'] = {}
				site['sitetype'][key] = row[index]
			elif 'sitedates' in key:
				if 'sitedates' not in site:
					site['sitedates'] = []
				# key looks like 'SiteDates_EventType_DateText'
				# row data looks like 'PorterMoss Date_Dynasty 5-6'
				# split on _ (and ignore first value in key)
				keys = key.split('_')[1:]
				values = row[index].split('_')
				date = {}
				for i, k in enumerate(keys):
					if values[i]:
						date[k.lower()] = values[i]
				if date:
					site['sitedates'].append(date)
			else:
				site[key] = row[index]
		print site

