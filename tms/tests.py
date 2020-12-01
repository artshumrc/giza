import json

from unittest import mock
from django.test import TestCase
from offline_scripts.utils import generate_iiif_manifest, generate_multi_canvas_iiif_manifest
from .views import get_manifest, get_sequence, get_canvas, get_annotation


MANIFEST = {
	"description": "A description of a manifest.",
	"@context": "https://iiif.io/api/presentation/2/context.json",
	"@id": "459673218",
	"label": "Some label",
	"sequences": [
		{
			"label": "Default order",
			"@type": "sc:Sequence",
			"@id": "459673218/sequence/0",
			"canvases": [
				{
					"@id": "459673218/canvas/0",
					"label": "1",
					"@type": "sc:Canvas",
					"width": 2616,
					"height": 1952,
					"images": [
						{
							"on": "459673218/canvas/0",
							"motivation": "sc:painting",
							"@type": "oa:Annotation",
							"@id": "459673218/annotation/canvas/0",
							"resource": {
								"width": 2616,
								"@id": "https://ids.lib.harvard.edu/ids/iiif/459673218/full/full/0/default.jpg",
								"@type": "dctypes:Image",
								"height": 1952,
								"service": {
								    "@context": "https://iiif.io/api/presentation/2/context.json",
									"@id": "https://ids.lib.harvard.edu/ids/iiif/459673218",
									"profile": "http://iiif.io/api/image/2/level1.json"
								}
							}
						}
					]    
				}
			]
		}
	],
	"@type": "sc:Manifest"
}

MULTI_MANIFEST = {
	"description": "A description of a manifest.",
	"@context": "https://iiif.io/api/presentation/2/context.json",
	"@id": "1",
	"label": "Some label",
	"sequences": [
		{
			"label": "Default order",
			"@type": "sc:Sequence",
			"@id": "1/sequence/0",
			"canvases": [
				{
					"@id": "1/canvas/0",
					"label": "1",
					"@type": "sc:Canvas",
					"width": 2616,
					"height": 1952,
					"images": [
						{
							"on": "1/canvas/0",
							"motivation": "sc:painting",
							"@type": "oa:Annotation",
							"@id": "1/annotation/canvas/0",
							"resource": {
								"width": 2616,
								"@id": "https://ids.lib.harvard.edu/ids/iiif/459673218/full/full/0/default.jpg",
								"@type": "dctypes:Image",
								"height": 1952,
								"service": {
								    "@context": "https://iiif.io/api/presentation/2/context.json",
									"@id": "https://ids.lib.harvard.edu/ids/iiif/459673218",
									"profile": "http://iiif.io/api/image/2/level1.json"
								}
							}
						}
					]    
				},
				{
				    "@id": "1/canvas/1",
				    "label": "2",
				    "@type": "sc:Canvas",
				    "width": 3000,
				    "height": 2000,
				    "images": [
					    {
						    "on": "1/canvas/1",
						    "motivation": "sc:painting",
						    "@type": "oa:Annotation",
						    "@id": "1/annotation/canvas/1",
						    "resource": {
							    "width": 3000,
							    "@id": "https://ids.lib.harvard.edu/ids/iiif/459003218/full/full/0/default.jpg",
							    "@type": "dctypes:Image",
							    "height": 2000,
							    "service": {
								    "@context": "https://iiif.io/api/presentation/2/context.json",
								    "@id": "https://ids.lib.harvard.edu/ids/iiif/459003218",
								    "profile": "http://iiif.io/api/image/2/level1.json"
							    }
						    }
					    }
					]
				}
			]
		}
	],
	"@type": "sc:Manifest"
}


def fake_get_manifest_data(req, id):
	return MANIFEST
	
def fake_get_multi_resource_manifest_data(req, id):
	return MULTI_MANIFEST


class UtilsTestCase(TestCase):
	
	def setUp(self):
		pass
		
	def tearDown(self):
		pass
		
	def test_generate_iiif_manifest(self):
		row = {
			"ArchIDNum": 459673218,
			"Description": "A description of a manifest.",
			"MediaView": "Some label"
		}
		self.assertEqual(generate_iiif_manifest(row), MANIFEST)
		
	def test_generate_multi_canvas_iiif_manifest(self):
		data = {
		    '1' : {
				'description': "A description of a manifest.",
				'label' : "Some label",
				'resources': [
				    {
						"width": 2616,
						"@id": "https://ids.lib.harvard.edu/ids/iiif/459673218/full/full/0/default.jpg",
						"@type": "dctypes:Image",
						"height": 1952,
						"service": {
							"@context": "https://iiif.io/api/presentation/2/context.json",
							"@id": "https://ids.lib.harvard.edu/ids/iiif/459673218",
							"profile": "http://iiif.io/api/image/2/level1.json"
						}
					},
				    {
						"width": 3000,
						"@id": "https://ids.lib.harvard.edu/ids/iiif/459003218/full/full/0/default.jpg",
						"@type": "dctypes:Image",
						"height": 2000,
						"service": {
							"@context": "https://iiif.io/api/presentation/2/context.json",
							"@id": "https://ids.lib.harvard.edu/ids/iiif/459003218",
							"profile": "http://iiif.io/api/image/2/level1.json"
						}
					}
				]
			}
		}
		self.assertEqual(generate_multi_canvas_iiif_manifest(1, data['1']), MULTI_MANIFEST)
		
class ViewsTestCase(TestCase):
	
	def setUp(self):
		pass
		
	@mock.patch("tms.views.get_manifest_data", fake_get_manifest_data)
	def test_get_manifest(self):
		self.assertEqual(json.loads(get_manifest(0, 0).content), MANIFEST)
		
	@mock.patch("tms.views.get_manifest_data", fake_get_manifest_data)
	def test_get_sequence(self):
		self.assertEqual(
			json.loads(get_sequence(0, 0).content),
			MANIFEST['sequences'][0]
			)
	
	@mock.patch("tms.views.get_manifest_data", fake_get_manifest_data)
	def test_get_canvas(self):
		self.assertEqual(
			json.loads(get_canvas(0, 0, 0).content),
			MANIFEST['sequences'][0]['canvases'][0]
			)
			
	@mock.patch("tms.views.get_manifest_data", fake_get_manifest_data)
	def test_get_annotation(self):
		self.assertEqual(
			json.loads(get_annotation(0, 0, 0).content),
			MANIFEST['sequences'][0]['canvases'][0]['images'][0]
			)
	
	@mock.patch("tms.views.get_manifest_data", fake_get_multi_resource_manifest_data)		
	def test_get_multi_resource_manifest(self):
		self.assertEqual(
		    json.loads(get_manifest(0, 0).content),
			MULTI_MANIFEST
		    )
	
	@mock.patch("tms.views.get_manifest_data", fake_get_multi_resource_manifest_data)		
	def test_get_single_annotation(self):
		# get the annotation by changing the canvas.
		# there is only ever one image per canvas
		self.assertEqual(
		    json.loads(get_annotation(0, 0, 1).content),
			MULTI_MANIFEST['sequences'][0]['canvases'][1]['images'][0]
		    )
		
