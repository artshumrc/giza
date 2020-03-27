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
		if isinstance(x, int):
			row.append(str(x))
		elif isinstance(x, str):
			row.append(x.encode('utf-8'))
		elif x is None:
			row.append("NULL")
		else:
			row.append(str(x))
	return row


def get_height_and_width(drs_id):
	""" return height and width from info.json """
	url = "https://ids.lib.harvard.edu/ids/iiif/{}/info.json".format(drs_id)
	r = requests.get(url)
	r.raise_for_status()
	j = r.json()
	return j["height"], j["width"]
	

def generate_IIIF_manifest(row):
	""" returns json representation of a IIIF manifest """
		
	manifest = build_base_manifest(row['ArchIDNum'], row['Description'], row['MediaView'])
	manifest["sequences"] = build_manifest_sequences(row['ArchIDNum'])
	manifest["sequences"][0]["canvases"] = build_manifest_canvas(row['ArchIDNum'])
	
	return manifest
	
def generate_site_IIIF_manifest(key, data):
	""" Compile all the resources associated with a site into one manifest """
	manifest = build_base_manifest(key, data['description'], data['label'])
	manifest["sequences"] = build_manifest_sequences(key)
	manifest["sequences"][0]["canvases"] = build_multi_image_canvas(key, data['resources'])
	return manifest


def build_base_manifest(drs_id, description, label):
	""" return the base IIIF manifest for the sequence to be added to """
	ob = {
	    "description": description,
		"@context": "https://iiif.io/api/presentation/2/context.json",
		"@id": "{}".format(drs_id),
		"label": label,
		"@type": "sc:Manifest"
	}
	return ob
	
	
def build_manifest_sequences(drs_id):
	""" return sequence list for IIIF manifest """
	seq_id = "{}/sequence/1".format(drs_id)
	seq = [
	    {
		    "label": "Default order",
			"@type": "sc:Sequence",
			"@id": seq_id
		}
	]
	return seq
	

def build_manifest_canvas(drs_id):
	""" return the IIF canvas to attach to a IIF sequence """
	canvas_id = "{}/canvas/1".format(drs_id)
	image_id = "{}/annotation/canvas/1".format(drs_id)
	resource_id = "https://ids.lib.harvard.edu/ids/iiif/{}/full/full/0/default.jpg".format(drs_id)
	height, width = get_height_and_width(drs_id)
	canvas = [
	    {
		    "@id": canvas_id,
			"label": "some label",
			"@type": "sc:Canvas",
			"width": width,
		    "height": height,
			"images": [
				{
					"on": canvas_id,
					"motivation": "sc:painting",
					"@type": "oa:Annotation",
					"@id": image_id,
					"resource": {
						"width": width,
						"@id": resource_id,
						"@type": "dctypes:Image",
						"height": height
					}
				}
			]
		}
	    
	]
	
	return canvas
	
def build_multi_image_canvas(id, resources_list):
	canvas_id = "{}/canvas/1".format(id)
	width = max([ob['width'] for ob in resources_list])
	height = max([ob['height'] for ob in resources_list])
	canvas = [
	    {
		    "@id": canvas_id,
			"label": "some label",
			"@type": "sc:Canvas",
			"width": width,
		    "height": height,
			"images": [
			    {
			        "on": canvas_id,
					"motivation": "sc:painting",
					"@type": "oa:Annotation",
					"@id": "{}/annotation/canvas/{}".format(id, idx),
					"resource": ob
			    }
			for idx, ob in enumerate(resources_list)
			]
		}
	    
	]
	return canvas
	
