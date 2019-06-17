

from builtins import next
import csv
import codecs
import elasticsearch_connection
import getpass
import json
import operator
import time
import unicodedata

from classifications import CLASSIFICATIONS, CONSTITUENTTYPES, MEDIATYPES
import published_sql
from utils import get_media_url, process_cursor_row

def delete_pubs():
	print("Deleting Pub Docs...")
	# delete pubs
	es = elasticsearch_connection.get_connection()
	es_index = elasticsearch_connection.ELASTICSEARCH_INDEX
	results = es.search(index=es_index, doc_type='pubdocs', body={
		"size" : 1000,
		"stored_fields" : ["_id"],
		"query": {
			"match_all" : {}
		}
	})['hits']['hits']
	for r in results:
		elasticsearch_connection.delete(r['_id'], 'pubdocs')
	print("Finished Deleting Pub Docs...")

# First update each Published doc with the latest data
# This is the basic information/metadata that comprises a Pubished document
def process_pubs(CURSOR):
	def get_indices():
		pub_id_index = columns.index('ID')
		return pub_id_index

	def process_pub_row(pub, current_id):
		pub_id = row[pub_id_index]

		if pub_id != current_id:
			save(pub)
			current_id = pub_id
			pub = {}

		# loop through columns in row
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

			pub[key] = row_value

		display_text = pub['title']
		pub['displaytext'] = display_text
		pub['roles'] = []
		pub["authors"] = []
		return (pub, current_id)

	print("Starting Pub Docs...")
	if CURSOR:
		sql_command = published_sql.PUBLISHED
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		pub_id_index = get_indices()

		pub = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(pub, current_id) = process_pub_row(pub, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(pub)

	else:
		with open('../data/pubdocs.csv', 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			pub_id_index = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			pub = {}
			current_id = '-1'
			for row in rows:
				(pub, current_id) = process_pub_row(pub, current_id)
			# save last object to elasticsearch
			save(pub)

	print("Finished Pub Docs...")

def process_pub_related_sites(CURSOR):
	def get_indices():
		indices = {
			'id_index' : columns.index('ReferenceID'),
			'site_id_index' : columns.index('SiteID'),
			'site_name_index' : columns.index('SiteName'),
			'site_number_index' : columns.index('SiteNumber'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_pub_row(pub, current_id):
		id = row[indices['id_index']]

		if id != current_id:
			save(pub)
			current_id = id
			pub = {}
			if elasticsearch_connection.item_exists(id, 'pubdocs'):
				pub = elasticsearch_connection.get_item(id, 'pubdocs')
			else:
				print("%s could not be found!" % id)
				return(pub, current_id)
		if 'relateditems' not in pub:
			pub['relateditems'] = {}

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

		if 'sites' not in pub['relateditems']:
			pub['relateditems']['sites'] = []
		pub['relateditems']['sites'].append(site_dict)
		# keep the related items sorted
		pub['relateditems']['sites'].sort(key=operator.itemgetter('displaytext'))

		return(pub, current_id)

	print("Starting Pub Docs Related Sites...")
	if CURSOR:
		sql_command = published_sql.RELATED_SITES
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		pub = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(pub, current_id) = process_pub_row(pub, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last pub to elasticsearch
		save(pub)
	else:
		with open('../data/pubdocs_sites_related.csv', 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			pub = {}
			current_id = '-1'
			for row in rows:
				(pub, current_id) = process_pub_row(pub, current_id)
			# save last pub to elasticsearch
			save(pub)

	print("Finished Pub Docs Related Sites...")

# Update all related items from the Objects table
def process_pub_related_objects(CURSOR):
	def get_indices():
		indices = {
			'pub_id_index' : columns.index('ReferenceID'),
			'classification_id_index' : columns.index('ClassificationID'),
			'object_id_index' : columns.index('ObjectID'),
			'object_title_index' : columns.index('Title'),
			'object_number_index' : columns.index('ObjectNumber'),
			'object_date_index' : columns.index('ObjectDate'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_pub_row(pub, current_id):
		pub_id = row[indices['pub_id_index']]

		if pub_id != current_id:
			save(pub)
			current_id = pub_id
			pub = {}
			if elasticsearch_connection.item_exists(pub_id, 'pubdocs'):
				pub = elasticsearch_connection.get_item(pub_id, 'pubdocs')
			else:
				print("%s could not be found!" % pub_id)
				return (pub, current_id)

		if 'relateditems' not in pub:
			pub['relateditems'] = {}
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

		if classification not in pub['relateditems']:
			pub['relateditems'][classification] = []
		pub['relateditems'][classification].append({
			'id' : object_id,
			'title' : object_title,
			'displaytext' : object_title,
			'classificationid' : classification_key,
			'number' : object_number,
			'date' : date,
			'thumbnail' : thumbnail_url})
		# keep the related items sorted
		pub['relateditems'][classification].sort(key=operator.itemgetter('displaytext'))

		return (pub, current_id)

	print("Starting Pub Docs Related Objects...")
	if CURSOR:
		sql_command = published_sql.RELATED_OBJECTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		pub = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(pub, current_id) = process_pub_row(pub, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(pub)
	else:
		with open('../data/pubdocs_objects_related.csv', 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			pub = {}
			current_id = '-1'
			for row in rows:
				(pub, current_id) = process_pub_row(pub, current_id)
			# save last object to elasticsearch
			save(pub)
	print("Finished Pub Docs Related Objects...")

# Next, update pub with all related Constituents
def process_pub_related_constituents(CURSOR):
	def get_indices():
		indices = {
			'pub_id_index' : columns.index('ReferenceID'),
			'role_index' : columns.index('Role'),
			'constituent_id_index' : columns.index('ConstituentID'),
			'constituent_type_id_index' : columns.index('ConstituentTypeID'),
			'display_name_index' : columns.index('DisplayName'),
			'alpha_sort_index' : columns.index('AlphaSort'),
			'display_date_index' : columns.index('DisplayDate'),
			'remarks_index' : columns.index('Remarks'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName')
		}
		return indices

	def process_pub_row(pub, current_id):
		pub_id = row[indices['pub_id_index']]

		if pub_id != current_id:
			# will likely have multiple rows for one pub because of many related constituents
			# only get a new pub if we have a new pub id, but first save old pub to elasticsearch
			save(pub)
			current_id = pub_id
			pub = {}
			if elasticsearch_connection.item_exists(pub_id, 'pubdocs'):
				pub = elasticsearch_connection.get_item(pub_id, 'pubdocs')
			else:
				print("%s could not be found!" % pub_id)
				return(pub, current_id)
		if 'relateditems' not in pub:
			pub['relateditems'] = {}

		constituent_id = row[indices['constituent_id_index']]
		display_name = row[indices['display_name_index']]
		display_date = ""
		if row[indices['display_date_index']] != "NULL":
			display_date = row[indices['display_date_index']]
		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])
		alpha_sort = row[indices['alpha_sort_index']]

		constituent_dict = {}
		role = row[indices['role_index']]
		# update the set of roles for this pub
		if role not in pub['roles']:
			pub['roles'].append(role)

		if role == "Author":
			pub["authors"].append(alpha_sort)

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
		if constituent_type not in pub['relateditems']:
			pub['relateditems'][constituent_type] = []
		pub['relateditems'][constituent_type].append(constituent_dict)
		# keep the related items sorted
		pub['relateditems'][constituent_type].sort(key=operator.itemgetter('displaytext'))

		return(pub, current_id)

	print("Starting Pub Docs Related Constituents...")
	if CURSOR:
		sql_command = published_sql.RELATED_CONSTITUENTS
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		pub = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(pub, current_id) = process_pub_row(pub, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(pub)
	else:
		with open('../data/pubdocs_constituents_related.csv', 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			pub = {}
			current_id = '-1'
			for row in rows:
				(pub, current_id) = process_pub_row(pub, current_id)
			# save last object to elasticsearch
			save(pub)

	print("Finished Pub Docs Related Constituents...")

# Update site with all related media
def process_pub_related_media(CURSOR):
	def get_indices():
		indices = {
			'pub_id_index' : columns.index('ReferenceID'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName'),
			'main_path_index' : columns.index('MainPathName'),
			'main_file_index' : columns.index('MainFileName')
		}
		return indices

	def process_pub_row(pub, current_id):
		pub_id = row[indices['pub_id_index']]

		if pub_id != current_id:
			save(pub)
			current_id = pub_id
			pub = {}
			if elasticsearch_connection.item_exists(pub_id, 'pubdocs'):
				pub = elasticsearch_connection.get_item(pub_id, 'pubdocs')
			else:
				print("%s could not be found!" % pub_id)
				return(pub, current_id)

		thumbnail_url = get_media_url(row[indices['thumb_path_index']], row[indices['thumb_file_index']])
		main_url = get_media_url(row[indices['main_path_index']], row[indices['main_file_index']])

		pub['primarydisplay'] = {
		'thumbnail' : thumbnail_url,
		'main' : thumbnail_url
		}
		pub['pdf'] = main_url

		return(pub, current_id)

	print("Starting Pub Docs Related Media...")
	if CURSOR:
		sql_command = published_sql.RELATED_MEDIA
		CURSOR.execute(sql_command)
		columns = [column[0] for column in CURSOR.description]
		indices = get_indices()

		pub = {}
		current_id = '-1'
		cursor_row = CURSOR.fetchone()
		while cursor_row is not None:
			row = process_cursor_row(cursor_row)
			(pub, current_id) = process_pub_row(pub, current_id)
			cursor_row = CURSOR.fetchone()
		   # save last object to elasticsearch
		save(pub)
	else:
		with open('../data/pubdocs_media_related.csv', 'r', encoding='utf-8-sig') as csvfile:
			# Get the query headers to use as keys in the JSON
			headers = next(csvfile)
			headers = headers.replace('\r\n','')
			headers = headers.replace('\n', '')
			columns = headers.split(',')
			indices = get_indices()

			rows = csv.reader(csvfile, delimiter=',', quotechar='"')
			pub = {}
			current_id = '-1'
			for row in rows:
				(pub, current_id) = process_pub_row(pub, current_id)
			# save last object to elasticsearch
			save(pub)

	print("Finished Pub Docs Related Media...")

# this groups published documents by author, for use on the Digital Giza Library page
def create_library():
	print("Creating Digital Library...")
	time.sleep(3) # for some reason the library isn't always fully populated. see if a time delay helps

	author_ids = []
	size = 20
	results_from = 0
	es = elasticsearch_connection.get_connection()
	es_index = elasticsearch_connection.ELASTICSEARCH_INDEX

	# delete library
	results = es.search(index=es_index, doc_type='library', body={
		"size" : 500,
		"stored_fields" : ["_id", "name"],
		"query": {
			"match_all" : {}
		}
	})['hits']['hits']
	for r in results:
		elasticsearch_connection.delete(r['_id'], 'library')

	total = es.search(index=es_index, doc_type='pubdocs', body={
		"size" : 0,
		"query": {
			"match_all" : {}
		}
	})['hits']['total']

	while results_from < total:
		results = es.search(index=es_index, doc_type='pubdocs', body={
			"size" : size,
			"from" : results_from,
			"query": {
				"match_all" : {}
			}
		})
		for r in results['hits']['hits']:
			result = r['_source']
			if 'pdf' not in result or result['pdf'] == '':
				continue
			authors = result['authors']

			# if this doc has no authors, set the author to 'No Author' and proceed
			if len(authors) == 0:
				authors.append('No Author')

			for author in authors:
				author_id = author.replace(' ', '')
				sortauthor = author.lower().strip()
				sortauthor = str(unicodedata.normalize('NFD', sortauthor).encode('ascii', 'ignore').decode("utf-8"))
				# see if this author already exists
				if author_id in author_ids:
					author_data = elasticsearch_connection.get_item(author_id, 'library')
				else:
					author_ids.append(author_id)
					author_data = {}
					author_data['name'] = author
					author_data['sortname'] = sortauthor
					author_data['docs'] = []

				author_data['docs'].append({
					'displaytext' : result['boilertext'],
					'sorttext' : result['notes'],
					'format' : result['format'],
					# add file size
					'url' : result['pdf']
				})
				author_data['docs'].sort(key=operator.itemgetter('sorttext'))

				data = json.dumps(author_data)
				elasticsearch_connection.add_or_update_item(author_id, data, 'library')

		results_from = results_from + size
	print("Finished Digital Library...")

def save(pub):
	if pub and 'id' in pub:
		elasticsearch_connection.add_or_update_item(pub['id'], json.dumps(pub), 'pubdocs')

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

	## delete_pubs and process_pubs MUST go first.  The other methods can go in any order
	delete_pubs()
	process_pubs(CURSOR)
	process_pub_related_sites(CURSOR)
	process_pub_related_objects(CURSOR)
	process_pub_related_constituents(CURSOR)
	process_pub_related_media(CURSOR)
	create_library()

if __name__ == "__main__":
	main()
