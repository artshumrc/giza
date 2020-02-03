import json

from unittest import mock
from django.test import TestCase
from offline_scripts.utils import generate_IIIF_manifest
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
			"@id": "459673218/sequence/1",
			"canvases": [
				{
					"@id": "459673218/canvas/1",
					"label": "some label",
					"@type": "sc:Canvas",
					"width": 2616,
					"height": 1952,
					"images": [
						{
							"on": "459673218/canvas/1",
							"motivation": "sc:painting",
							"@type": "oa:Annotation",
							"@id": "459673218/annotation/canvas/1",
							"resource": {
								"width": 2616,
								"@id": "https://ids.lib.harvard.edu/ids/iiif/459673218/full/full/0/default.jpg",
								"@type": "dctypes:Image",
								"height": 1952
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


class UtilsTestCase(TestCase):
	
	def setUp(self):
		pass
		
	def tearDown(self):
		pass
		
	def test_generate_IIIF_manifest(self):
		row = {
			"ArchIDNum": 459673218,
			"Description": "A description of a manifest.",
			"MediaView": "Some label"
		}
		self.assertEqual(generate_IIIF_manifest(row), MANIFEST)
		
		
class ViewsTestCase(TestCase):
	
	def setUp(self):
		pass
		
	@mock.patch("tms.views.get_manifest_data", fake_get_manifest_data)
	def test_get_manifest(self):
		self.assertEqual(json.loads(get_manifest(0, 0).content), MANIFEST)
		
	@mock.patch("tms.views.get_manifest_data", fake_get_manifest)
	def test_get_sequence(self):
		self.assertEqual(
			json.loads(get_sequence(0, 0).content),
			MANIFEST['sequences'][0]
			)
	
	@mock.patch("tms.views.get_manifest_data", fake_get_manifest_data)
	def test_get_canvas(self):
		self.assertEqual(
			json.loads(get_canvas(0, 0).content),
			MANIFEST['sequences'][0]['canvases'][0]
			)
			
	@mock.patch("tms.views.get_manifest_data", fake_get_manifest_data)
	def test_get_annotation(self):
		self.assertEqual(
			json.loads(get_annotation(0, 0).content),
			MANIFEST['sequences'][0]['canvases'][0]['images'][0]
			)
		
