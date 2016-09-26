from django.conf.urls import include, url
from django.conf import settings
from django.contrib import admin

from wagtail.wagtailadmin import urls as wagtailadmin_urls
from wagtail.wagtaildocs import urls as wagtaildocs_urls
from wagtail.wagtailcore import urls as wagtail_urls


urlpatterns = [
    url(r'^$', 'tms.views.index', name="index"),
    url(r'^(?P<page_name>about|blog|contact|gizacard|news|resources)/$', 'tms.views.about', name="about"),
    url(r'^(?P<page_name>donate)/$', 'tms.views.donate', name="donate"),
    url(r'^(?P<page_name>archeology|commontopics|explorevideos|faq|gizaintro)/$', 'tms.views.explore', name="explore"),

    url(r'^django-admin/', include(admin.site.urls)),

    url(r'^admin/', include(wagtailadmin_urls)),
    url(r'^documents/', include(wagtaildocs_urls)),

    url(r'^search/$', 'search.views.search', name='search'),
    url(r'^search-results/$', 'search.views.results', name='results'),

    url(r'^(?P<type>[a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full)?/$', 'tms.views.get_type_html', name='get_type_html'),
    url(r'^(?P<type>[a-z]+)/(?P<id>[\d]+)\.json$', 'tms.views.get_type_json', name='get_type_json'),

    url(r'', include(wagtail_urls)),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns
    from django.views.generic import TemplateView

    # Serve static and media files from development server
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
