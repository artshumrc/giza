from __future__ import annotations

from .models import StaticTemplatePage


EXPECTED_ITEM_COUNT = 158_968
EXPECTED_MANIFEST_COUNT = 134_580
IIIF_CACHE_HOST = "iiif-cache.digitalhumanities.fas.harvard.edu"
IIIF_CACHE_MANIFEST_URL = f"https://{IIIF_CACHE_HOST}/iiif/manifest?manifest="
IIIF_CACHE_THUMB_URL = f"https://{IIIF_CACHE_HOST}/iiif/thumb?url="

# Every media URL in the site is <media base>/<path>, where <path> is the same
# server-relative path the retired gizamedia host used and is also the S3 key in
# the giza-media bucket. Change the base here (or with --media-base-url) and the
# whole build follows; nothing else should name a media host.
DEFAULT_MEDIA_BASE_URL = "https://d1g9lvwdq3dcse.cloudfront.net"

# Hosts that served those same paths before the move to CloudFront. Absolute
# URLs to them are baked into the ES export, so the build rewrites them on the
# way out rather than reindexing the data.
LEGACY_MEDIA_HOSTS = ("gizamedia.rc.fas.harvard.edu",)

# Paths the TMS records still point at that no longer match the drive: folders
# renamed with working notes ("_remove from TMS Collections"), a stray trailing
# space, and a mojibake spelling of BÄM. The files themselves are all present,
# so the build redirects the reference instead of emitting a dead link.
# Regenerate with media_catalog.py, which derives each row by resolving the
# reference against the real bucket listing.
MEDIA_PATH_REPAIRS_FILE = "media_path_repairs.tsv"

# The Berlin museum folder (BÄM) survives in the TMS records in several mangled
# spellings, depending on which encoding round-trip damaged each one. These are
# fixed before the path is read, not through the repairs file, because the
# ``BA?M`` form contains a literal '?' that would otherwise be taken for the
# start of a query string and truncate the path.
MEDIA_MOJIBAKE_REPAIRS = (
    ("BA?M", "BÄM"),
    ("BŽM", "BÄM"),
    ("BÃ„M", "BÄM"),
)

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
