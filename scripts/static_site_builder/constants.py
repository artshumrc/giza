from __future__ import annotations

from .models import StaticTemplatePage


EXPECTED_ITEM_COUNT = 158_968
EXPECTED_MANIFEST_COUNT = 134_580
IIIF_CACHE_HOST = "iiif-cache.digitalhumanities.fas.harvard.edu"
IIIF_CACHE_THUMB_URL = f"https://{IIIF_CACHE_HOST}/iiif/thumb?url="

TYPE_LABELS = {
    "3dmodels": "3D Models",
    "ancientpeople": "Ancient People",
    "animals": "Animals",
    "diarypages": "Diary Pages",
    "drawings": "Drawings",
    "groups": "Groups",
    "institutions": "Institutions",
    "mapsandplans": "Maps and Plans",
    "modernpeople": "Modern People",
    "objects": "Objects",
    "photos": "Photos",
    "pubdocs": "Published Documents",
    "sites": "Sites",
    "unpubdocs": "Unpublished Documents",
    "videos": "Videos",
}

SEARCH_CATEGORY_ORDER = [
    ("photos", "Photos"),
    ("objects", "Objects"),
    ("unpubdocs", "Unpublished Documents"),
    ("mapsandplans", "Maps and Plans"),
    ("diarypages", "Diary Pages"),
    ("drawings", "Drawings"),
    ("sites", "Tombs and Monuments"),
    ("ancientpeople", "Ancient People"),
    ("videos", "Videos"),
    ("modernpeople", "Modern People"),
    ("pubdocs", "Published Documents"),
    ("institutions", "Institutions"),
    ("3dmodels", "3D Models"),
    ("groups", "Groups"),
    ("animals", "Animals"),
]

SEARCH_CATEGORY_LABELS = dict(SEARCH_CATEGORY_ORDER)

STATIC_TEMPLATE_PAGES = [
    StaticTemplatePage(
        "about",
        "about.html",
        "About the Giza Project",
        "About the Giza Project at Harvard University.",
    ),
    StaticTemplatePage(
        "blog", "blog.html", "The Giza Project Blog", "The Giza Project blog."
    ),
    StaticTemplatePage(
        "contact", "contact.html", "Contact Us", "Contact information for Digital Giza."
    ),
    StaticTemplatePage(
        "gizacard",
        "gizacard.html",
        "The GizaCARD",
        "The data model behind Digital Giza.",
    ),
    StaticTemplatePage("news", "news.html", "News", "Digital Giza news."),
    StaticTemplatePage(
        "resources",
        "resources.html",
        "Educational Resources",
        "Educational resources from Digital Giza.",
    ),
    StaticTemplatePage(
        "sampleblog",
        "sampleblogpost.html",
        "The Giza Project Blog",
        "Sample Giza Project blog post.",
    ),
    StaticTemplatePage("donate", "donate.html", "Donate", "Support the Giza Project."),
    StaticTemplatePage(
        "gizaintro",
        "gizaintro.html",
        "Introduction to Giza",
        "Introduction to the Giza Plateau.",
    ),
    StaticTemplatePage(
        "archaeology",
        "archaeology.html",
        "Archaeology at Giza",
        "Archaeology and excavation history at Giza.",
    ),
    StaticTemplatePage(
        "commontopics",
        "commontopics.html",
        "People and Places of Giza",
        "Common topics about Giza.",
    ),
    StaticTemplatePage(
        "faq",
        "faq.html",
        "Frequently Asked Questions",
        "Glossary and frequently asked questions.",
    ),
    StaticTemplatePage(
        "gizaatschool",
        "gizaatschool.html",
        "Giza @ School",
        "Teaching resources for Giza.",
    ),
    StaticTemplatePage(
        "giza3d", "giza3d.html", "Giza 3D", "Giza 3D resources and model links."
    ),
]
