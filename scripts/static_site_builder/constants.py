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

RELATED_TYPE_ALIASES = {
    "giza3d": "3dmodels",
    "models": "3dmodels",
    "plansanddrawings": "drawings",
}

RELATED_SECTION_LABELS = {
    "3dmodels": "3D Models",
    "ancientpeople": "Ancient People",
    "animals": "Animals",
    "audio": "Audio",
    "diarypages": "Excavation Diary Pages",
    "drawings": "Drawings",
    "groups": "Groups",
    "institutions": "Institutions",
    "mapsandplans": "Maps and Plans",
    "modernpeople": "Modern People",
    "objects": "Finds",
    "photos": "Photos",
    "pubdocs": "Published Documents",
    "sites": "Tombs and Monuments",
    "unpubdocs": "Unpublished Documents",
    "videos": "Videos",
}

RELATED_SECTION_ICONS = {
    "sites": "map-marker",
    "objects": "vase",
    "diarypages": "sticky-note-o",
    "mapsandplans": "map-o",
    "drawings": "pencil-square-o",
    "pubdocs": "book",
    "unpubdocs": "file-text-o",
    "3dmodels": "pyramid-3d",
    "videos": "video-camera",
    "ancientpeople": "user",
    "modernpeople": "user",
    "institutions": "university",
    "groups": "users",
    "animals": "paw",
    "audio": "music",
}

RELATED_ORDER = [
    "sites",
    "objects",
    "diarypages",
    "mapsandplans",
    "drawings",
    "photos",
    "3dmodels",
    "giza3d",
    "videos",
    "audio",
    "ancientpeople",
    "modernpeople",
    "institutions",
    "groups",
    "animals",
    "pubdocs",
    "unpubdocs",
]

DETAIL_FIELDS = [
    ("Type", "constituenttype", "text"),
    ("ID", "number", "text"),
    ("Alternate IDs", "allnumbers", "text"),
    ("Site Name", "sitename", "text"),
    ("Site Type", "sitetype", "text"),
    ("Site Dates", "sitedates", "text"),
    ("Tomb Owner", "tombowner", "text"),
    ("Department", "department", "text"),
    ("Classification", "classificationtext", "text"),
    ("Period", "period", "text"),
    ("Date", "date", "text"),
    ("Entry Date", "entrydate", "text"),
    ("Title", "title", "text"),
    ("Medium", "medium", "text"),
    ("Dimensions", "dimensions", "text"),
    ("Credit Line", "creditline", "text"),
    ("Provenance", "provenance", "text"),
    ("Authors", "authors", "text"),
    ("Year Published", "yearpublished", "text"),
    ("Format", "format", "text"),
    ("Language", "language", "text"),
    ("Pages", "numofpages", "text"),
    ("Journal", "journal", "text"),
    ("Series", "series", "text"),
    ("Subjects", "subjects", "text"),
    ("Media View", "mediaview", "text"),
    ("Nationality", "nationality", "text"),
    ("Display Date", "displaydate", "text"),
    ("Institution", "institution", "text"),
    ("Gender", "gender", "text"),
    ("Also Known As", "altnames", "altnames"),
    ("Citation", "boilertext", "safe_html"),
    ("Notes", "notes", "text"),
    ("Remarks", "remarks", "text"),
    ("Research Activity", "researchactivity", "text"),
    ("Researcher Comments", "researchercomments", "text"),
    ("Condition", "condition", "text"),
    ("Location Notes", "locationnotes", "text"),
    ("Problems/Questions", "problemsquestions", "text"),
]

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
