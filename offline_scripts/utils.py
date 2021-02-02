import requests
import json
import os
import csv

from builtins import str

# January 2021: this URL pattern will change
IIIF_IMAGE_SERVER_PREFIX = "https://ids.lib.harvard.edu/ids/iiif/"
IIIF_THUMBNAIL_SYNTAX = "/full/200,/0/default.jpg"

DIRNAME = os.path.dirname(__file__)

def get_media_url(path, filename):
	if 'nrs.harvard.edu' in path:
		return path + '/' + filename
	idx = path.find('images')
	if idx == -1:
		idx = path.find('documents')
		if idx == -1:
			return ""
	if filename.endswith('bmp'):
		return ""
	path = path[idx:].replace('\\','/')
	if not path.endswith('/'):
		path = path + '/'
	url = 'http://gizamedia.rc.fas.harvard.edu/' + path + filename
	return url


def process_cursor_row(cursor_row):
	row = []
	for x in cursor_row:
		if x is None:
			row.append("NULL")
		else:
			row.append(str(x))
	return row

def create_thumbnail_url(id):
	return "{}{}{}".format(IIIF_IMAGE_SERVER_PREFIX, id, IIIF_THUMBNAIL_SYNTAX)

def get_height_and_width(id):
	""" return height and width from info.json """
	# first check height/width csv file if we can avoid a network call
	width = 0
	height = 0
	with open(os.path.join(DIRNAME, '..', 'data', 'drs_ids_height_width.csv'), 'r', encoding='utf-8-sig') as csvfile:
		headers = next(csvfile)
		rows = csv.reader(csvfile, delimiter=",")
		for row in rows:
			if id in row[0]:
				#print("Found DRS ID in CSV file")
				height = int(row[1])
				width = int(row[2])
	if width == 0 and height == 0:
		print("DRS ID not found in CSV file, requesting from IIIF server")
		url = "https://ids.lib.harvard.edu/ids/iiif/{}/info.json".format(id)
		r = requests.get(url)
		r.raise_for_status()
		j = r.json()
		return j["height"], j["width"]
	else:
		return height, width


def generate_iiif_manifest(row):
	""" returns json representation of a IIIF manifest """
	manifest = build_base_manifest(row['ManifestID'], row['Description'], row['MediaView'])
	manifest["sequences"] = build_manifest_sequences(row['ManifestID'])
	manifest["sequences"][0]["canvases"] = [build_manifest_canvas(row['ManifestID'], row['ArchIDNum'], 0, None)]
	return manifest


def generate_multi_canvas_iiif_manifest(manifest_id, data):
	""" Compile all the resources associated with a site into one manifest """
	manifest = build_base_manifest(manifest_id, data['description'], data['label'])
	manifest["sequences"] = build_multi_image_sequence(manifest_id, data['resources'], data['drs_ids'])
	for canvas in manifest["sequences"][0]["canvases"]:
		if "startCanvas" in data and data["startCanvas"] in canvas["images"][0]["resource"]["service"]["@id"]:
			manifest["sequences"][0]["startCanvas"] = canvas["@id"]
	return manifest


def build_base_manifest(manifest_id, description, label):
	""" return the base IIIF manifest for the sequence to be added to """
	ob = {
	    "description": description,
		"@context": "https://iiif.io/api/presentation/2/context.json",
		"@id": "{}".format(manifest_id),
		"label": label,
		"@type": "sc:Manifest"
	}
	return ob


def build_manifest_sequences(id):
	""" return sequence list for IIIF manifest """
	seq_id = "{}/sequence/0".format(id)
	seq = [
	    {
		    "label": "Default order",
			"@type": "sc:Sequence",
			"@id": seq_id
		}
	]
	return seq


def build_multi_image_sequence(manifest_id, resources_list, drs_ids):
	""" return sequence list of canvases each with one image """
	seq_id = "{}/sequence/0".format(manifest_id)
	seq = [
	    {
		    "label": "Default order",
			"@type": "sc:Sequence",
			"@id": seq_id,
			"canvases": []
		}
	]
	for idx, resource in enumerate(resources_list):
		seq[0]['canvases'].append(build_manifest_canvas(manifest_id, drs_ids[idx], idx, resource))
	return seq


def build_manifest_canvas(manifest_id, drs_id, idx, resource):
	if resource is None:
		resource = build_resource(drs_id)
	canvas_id = "{}/canvas/{}".format(manifest_id, idx)
	canvas = {
	    "@id": canvas_id,
		"label": str(idx+1),
		"@type": "sc:Canvas",
		"width": resource['width'],
		"height": resource['height'],
		"images": [
		    {
			    "on": canvas_id,
				"motivation": "sc:painting",
				"@type": "oa:Annotation",
				"@id": "{}/annotation/canvas/{}".format(manifest_id, idx),
				"resource": resource
			}
		]
	}
	return canvas


def build_resource(id):
	height, width = get_height_and_width(id)
	service = {
	    "@context": "https://iiif.io/api/presentation/2/context.json",
	    "@id": "https://ids.lib.harvard.edu/ids/iiif/{}".format(id),
		"profile": "http://iiif.io/api/image/2/level1.json"
	}
	resource = {
	    "width": width,
	    "@id": "https://ids.lib.harvard.edu/ids/iiif/{}/full/full/0/default.jpg".format(id),
	    "@type": "dctypes:Image",
	    "height": height,
	    "service": service
	}
	return resource
