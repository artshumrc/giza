"""giza URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
	https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
	1. Add an import:  from my_app import views
	2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
	1. Add an import:  from other_app.views import Home
	2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
	1. Import the include() function: from django.conf.urls import url, include
	2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.urls import path
from django.contrib import admin
from tms import views as tms_views
from search import views as search_views

urlpatterns = [
	url(r'^$', tms_views.index, name="index"),
	url(r'^(?P<page_name>about|blog|contact|gizacard|news|resources|sampleblog)/$', tms_views.about, name="about"),
	url(r'^(?P<page_name>donate)/$', tms_views.donate, name="donate"),
	url(r'^(?P<page_name>archaeology|commontopics|faq|gizaintro)/$', tms_views.explore, name="explore"),
	url(r'^library/$', search_views.library, name="library"),
	url(r'^explorevideos/$', search_views.videos, name="explorevideos"),

	url(r'^search/$', search_views.search, name='search'),
	url(r'^search-results/$', search_views.results, name='results'),
	
	path('manifests/<int:id>/', tms_views.get_manifest, {'level': 'manifest'}, name="iiif-manifest"),
	path('manifests/<int:id>/sequence/1/', tms_views.get_manifest, {'level': 'sequence'}, name="iiif-manifest-sequence"),
	path('manifests/<int:id>/canvas/1/', tms_views.get_manifest, {'level': 'canvas'}, name="iiif-manifest-canvas"),
	path('manifests/<int:id>/annotation/canvas/1/', tms_views.get_manifest, {'level': 'annotation'}, name="iiif-manifest-annotation"),

	url(r'^(?P<type>[0-9a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full|allphotos)?/$', tms_views.get_type_html, name='get_type_html'),
	url(r'^(?P<type>[0-9a-z]+)/(?P<id>[\d]+)\.json$', tms_views.get_type_json, name='get_type_json'),

	url(r'^admin/', admin.site.urls),
]
