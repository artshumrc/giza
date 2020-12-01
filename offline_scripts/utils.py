import requests
import json

from builtins import str


def get_media_url(path, filename):
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


def get_height_and_width(id):
	""" return height and width from info.json """
	url = "https://ids.lib.harvard.edu/ids/iiif/{}/info.json".format(id)
	r = requests.get(url)
	r.raise_for_status()
	j = r.json()
	return j["height"], j["width"]


def generate_iiif_manifest(row):
	""" returns json representation of a IIIF manifest """
	manifest = build_base_manifest(row['ArchIDNum'], row['Description'], row['MediaView'])
	manifest["sequences"] = build_manifest_sequences(row['ArchIDNum'])
	manifest["sequences"][0]["canvases"] = [build_manifest_canvas(row['ArchIDNum'], 0, None)]
	return manifest


def generate_multi_canvas_iiif_manifest(key, data):
	""" Compile all the resources associated with a site into one manifest """
	manifest = build_base_manifest(key, data['description'], data['label'])
	manifest["sequences"] = build_multi_image_sequence(key, data['resources'])
	for canvas in manifest["sequences"][0]["canvases"]:
		if "startCanvas" in data and data["startCanvas"] in canvas["images"][0]["resource"]["service"]["@id"]:
			manifest["sequences"][0]["startCanvas"] = canvas["@id"]
			print (manifest)
	return manifest


def build_base_manifest(id, description, label):
	""" return the base IIIF manifest for the sequence to be added to """
	ob = {
	    "description": description,
		"@context": "https://iiif.io/api/presentation/2/context.json",
		"@id": "{}".format(id),
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


def build_multi_image_sequence(id, resources_list):
	""" return sequence list of canvases each with one image """
	seq_id = "{}/sequence/0".format(id)
	seq = [
	    {
		    "label": "Default order",
			"@type": "sc:Sequence",
			"@id": seq_id,
			"canvases": []
		}
	]
	for idx, resource in enumerate(resources_list):
		seq[0]['canvases'].append(build_manifest_canvas(id, idx, resource))
	return seq


def build_manifest_canvas(id, idx, resource):
	if resource is None:
		resource = build_resource(id)
	canvas_id = "{}/canvas/{}".format(id, idx)
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
				"@id": "{}/annotation/canvas/{}".format(id, idx),
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
