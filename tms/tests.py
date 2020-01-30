import json

from django.test import TestCase
from offline_scripts.utils import generate_IIIF_manifest


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
        self.assertEqual(json.loads(generate_IIIF_manifest(row)), MANIFEST)
