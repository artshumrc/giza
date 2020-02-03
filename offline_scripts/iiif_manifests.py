import csv
import elasticsearch_connection
import json

from utils import generate_IIIF_manifest


ARCH_IDS = []


def process_sites_objects_related_manifests():
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
		
	with open('../data/sites_objects_related.csv', 'r', encoding="utf-8-sig") as csvfile:
		# Get the query headers to use as keys in the JSON
		headers = next(csvfile)
		headers = headers.replace('\r\n','')
		headers = headers.replace('\n','')
		columns = headers.split(',')
		indices = get_indices()
	
		rows = csv.reader(csvfile, delimiter=',', quotechar='"')
		object = {}
		current_id = '-1'
		for row in rows:
			if not row[indices['drs_id']].lower() == "null" and row[indices['drs_id']] not in ARCH_IDS:
				manifest_ob = {
					"ArchIDNum": row[indices['drs_id']],
					"Description": row[indices['object_title_index']],
					"MediaView": row[indices['object_number_index']]
				}
				object = {
					"id": row[indices['drs_id']],
					"manifest": generate_IIIF_manifest(manifest_ob)
				}
				save(object)
				ARCH_IDS.append(row[indices['drs_id']])


def process_sites_media_related_manifests():
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
	
	with open('../data/sites_media_related.csv', 'r', encoding="utf-8-sig") as csvfile:
		# Get the query headers to use as keys in the JSON
		headers = next(csvfile)
		headers = headers.replace('\r\n','')
		headers = headers.replace('\n','')
		columns = headers.split(',')
		indices = get_indices()
	
		rows = csv.reader(csvfile, delimiter=',', quotechar='"')
		object = {}
		current_id = '-1'
		for row in rows:
			if not row[indices['drs_id']].lower() == "null" and row[indices['drs_id']] not in ARCH_IDS:
				manifest_ob = {
					"ArchIDNum": row[indices['drs_id']],
					"Description": row[indices['description_index']],
					"MediaView": row[indices['media_view_index']]
				}
				object = {
					"id": row[indices['drs_id']],
					"manifest": generate_IIIF_manifest(manifest_ob)
				}
				save(object)
				ARCH_IDS.append(row[indices['drs_id']])


def process_object_sites_related_manifests():
	def get_indices():
		indices = {
			'id_index' : columns.index('ID'),
			'site_id_index' : columns.index('SiteID'),
			'site_name_index' : columns.index('SiteName'),
			'site_number_index' : columns.index('SiteNumber'),
			'classification_id_index' : columns.index('ClassificationID'),
			'thumb_path_index' : columns.index('ThumbPathName'),
			'thumb_file_index' : columns.index('ThumbFileName'),
			'drs_id' : columns.index('ArchIDNum')
		}
		
	
	with open('../data/objects_sites_related.csv', 'r', encoding="utf-8-sig") as csvfile:
		# Get the query headers to use as keys in the JSON
		headers = next(csvfile)
		headers = headers.replace('\r\n','')
		headers = headers.replace('\n','')
		columns = headers.split(',')
		indices = get_indices()
	
		rows = csv.reader(csvfile, delimiter=',', quotechar='"')
		object = {}
		current_id = '-1'
		for row in rows:
			if not row[indices['drs_id']].lower() == "null" and row[indices['drs_id']] not in ARCH_IDS:
				manifest_ob = {
					"ArchIDNum": row[indices['drs_id']],
					"Description": row[indices['site_name_index']],
					"MediaView": row[indices['site_number_index']]
				}
				object = {
					"id": row[indices['drs_id']],
					"manifest": generate_IIIF_manifest(manifest_ob)
				}
				save(object)
				ARCH_IDS.append(row[indices['drs_id']])


def process_object_media_related_manifests():
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
			'main_file_index' : columns.index('MainFileName'),
			'drs_id' : columns.index('ArchIDNum')
		}
		return indices
		
	with open('../data/objects_media_related.csv', 'r', encoding="utf-8-sig") as csvfile:
		# Get the query headers to use as keys in the JSON
		headers = next(csvfile)
		headers = headers.replace('\r\n','')
		headers = headers.replace('\n','')
		columns = headers.split(',')
		indices = get_indices()
	
		rows = csv.reader(csvfile, delimiter=',', quotechar='"')
		object = {}
		current_id = '-1'
		for row in rows:
			if not row[indices['drs_id']].lower() == "null" and row[indices['drs_id']] not in ARCH_IDS:
				manifest_ob = {
					"ArchIDNum": row[indices['drs_id']],
					"Description": row[indices['description_index']],
					"MediaView": row[indices['media_view_index']]
				}
				object = {
					"id": row[indices['drs_id']],
					"manifest": generate_IIIF_manifest(manifest_ob)
				}
				save(object)
				ARCH_IDS.append(row[indices['drs_id']])
				
	
def save(manifest):
	if manifest and 'id' in manifest:
		elasticsearch_connection.add_or_update_item(manifest['id'], json.dumps(manifest), 'iiif_manifest')

def main():
	process_object_media_related_manifests()
	process_sites_media_related_manifests()
	process_object_sites_related_manifests()
	process_sites_objects_related_manifests()

if __name__ == "__main__":
	main()
