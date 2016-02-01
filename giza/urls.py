from django.conf.urls import include, url
from django.conf import settings
from django.contrib import admin

from wagtail.wagtailadmin import urls as wagtailadmin_urls
from wagtail.wagtaildocs import urls as wagtaildocs_urls
from wagtail.wagtailcore import urls as wagtail_urls


urlpatterns = [
    url(r'^django-admin/', include(admin.site.urls)),

    url(r'^admin/', include(wagtailadmin_urls)),
    url(r'^documents/', include(wagtaildocs_urls)),

    url(r'^$', 'tms.views.index', name="index"),

    url(r'^search/$', 'search.views.search', name='search'),

    url(r'^sites/(?P<id>[\d]+)/?$', 'tms.views.site', name='sites'),
    url(r'^sites/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.site_related_items', name='get_site_related_items'),

    url(r'^finds/(?P<id>[\d]+)/?$', 'tms.views.find', name='finds'),
    url(r'^finds/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.find_related_items', name='get_find_related_items'),

    url(r'^diarypages/(?P<id>[\d]+)/?$', 'tms.views.diarypage', name='diarypages'),
    url(r'^diarypages/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.diarypage_related_items', name='get_diarypage_related_items'),
    
    url(r'^ancientpeople/(?P<id>[\d]+)/?$', 'tms.views.ancientperson', name='ancientpeople'),
    url(r'^ancientpeople/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.ancientperson_related_items', name='get_ancientperson_related_items'),

    url(r'^modernpeople/(?P<id>[\d]+)/?$', 'tms.views.modernperson', name='modernpeople'),
    url(r'^modernpeople/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.modernperson_related_items', name='get_modernperson_related_items'),

    url(r'^institutions/(?P<id>[\d]+)/?$', 'tms.views.institution', name='institutions'),
    url(r'^institutions/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.institution_related_items', name='get_institution_related_items'),

    url(r'^groups/(?P<id>[\d]+)/?$', 'tms.views.group', name='groups'),
    url(r'^groups/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.group_related_items', name='get_group_related_items'),

    url(r'^animals/(?P<id>[\d]+)/?$', 'tms.views.animal', name='animals'),
    url(r'^animals/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.animal_related_items', name='get_animal_related_items'),

    url(r'^photos/(?P<id>[\d]+)/?$', 'tms.views.photo', name='photos'),
    url(r'^photos/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.photo_related_items', name='get_photo_related_items'),

    url(r'^plansanddrawings/(?P<id>[\d]+)/?$', 'tms.views.plansanddrawings', name='plansanddrawings'),
    url(r'^plansanddrawings/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.plansanddrawings_related_items', name='get_plansanddrawings_related_items'),

    url(r'^pubdocs/(?P<id>[\d]+)/?$', 'tms.views.pubdoc', name='pubdocs'),
    url(r'^pubdocs/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.pubdoc_related_items', name='get_pubdoc_related_items'),

    url(r'^unpubdocs/(?P<id>[\d]+)/?$', 'tms.views.unpubdoc', name='unpubdocs'),
    url(r'^unpubdocs/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.unpubdoc_related_items', name='get_unpubdoc_related_items'),

    url(r'', include(wagtail_urls)),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from django.views.generic import TemplateView

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
