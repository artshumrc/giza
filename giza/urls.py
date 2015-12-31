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

    url(r'^photos/(?P<id>[\d]+)/?$', 'tms.views.photo', name='photos'),
    url(r'^photos/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.photo_related_items', name='get_photo_related_items'),

    url(r'^plansanddrawings/(?P<id>[\d]+)/?$', 'tms.views.plansanddrawings', name='plansanddrawings'),
    url(r'^plansanddrawings/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.plansanddrawings_related_items', name='get_plansanddrawings_related_items'),

    url(r'^publisheddocuments/(?P<id>[\d]+)/?$', 'tms.views.publisheddocument', name='publisheddocuments'),
    url(r'^publisheddocuments/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.publisheddocument_related_items', name='get_publisheddocument_related_items'),

    url(r'^unpublisheddocuments/(?P<id>[\d]+)/?$', 'tms.views.unpublisheddocument', name='unpublisheddocuments'),
    url(r'^unpublisheddocuments/(?P<id>[\d]+)/(?P<relation>[a-z]+)/?$', 'tms.views.unpublisheddocument_related_items', name='get_unpublisheddocument_related_items'),

    url(r'', include(wagtail_urls)),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from django.views.generic import TemplateView

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
