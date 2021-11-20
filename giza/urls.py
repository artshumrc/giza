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
from django.conf.urls import include
from django.contrib import admin
from tms import views as tms_views
from search import views as search_views
from . import views

urlpatterns = [
    url(r'^$', tms_views.index, name="index"),

    url(r'^(?P<page_name>about|blog|contact|gizacard|news|resources|sampleblog)/$', tms_views.about, name="about"),

    url(r'^(?P<page_name>donate)/$', tms_views.donate, name="donate"),

    url(r'^(?P<page_name>archaeology|commontopics|faq|gizaintro|gizaatschool|giza3d)/$', tms_views.explore, name="explore"),

    url(r'^lessons/(?P<slug>[\w-]+)$', views.lesson, name="lesson"),
    url(r'^lessons/$', views.lessons, name="lessons"),
    url(r'^collections/user$', views.collections_user, name="collections_user"),
    url(r'^collections/create$', views.collections_create, name="collections_create"),
    url(r'^collections/(?P<slug>[\w-]+)$', views.collection, name="collection"),
    url(r'^collections/(?P<slug>[\w-]+)/edit$', views.collections_edit, name="collection_edit"),
    # url(r'^collections/add/<slug:slug>', views.collections_add, name="collections_add"),
    # url(r'^collections/edit/<uuid:uuid>', views.collections_edit, name="collection_edit"),
    url(r'^collections/all/$', views.collections, name="collections"),
    url(r'^search/all/del/(?P<token>[\w-]+)$', views.search_del, name='search_del'),
    url(r'^search/all/$', views.search_all, name="search_all"),
    url(r'^search/lookup', views.search_token, name='search_token'),
    url(r'^mygiza/$', views.mygiza, name="mygiza"),
    url(r'^library/$', search_views.library, name="library"),
    url(r'^videos/$', search_views.videos, name="videos"),
    url(r'^search/results/$', search_views.search_results, name='search_results'),
    url(r'^search/$', search_views.search, name='search'),
    url(r'^search/show/$', search_views.search_show, name='search_show'),
    url(r'^search/update', search_views.search_update, name='update_search'),

    # url(r'^search/show/$', search_views.searchResultsView.as_view(), name='search_show'),
    url(r'^search/save$', views.search_save, name='search_save'),

    # auth
	# TODO for password change/reset, implement django accounts auth
    # path('accounts/', include('django.contrib.auth.urls')),
    url('sign-up/', views.sign_up, name='sign_up'),
    url('login/', views.user_login, name='login'),
    url('logout/', views.user_logout, name='logout'),

	path('manifests/<slug:id>/', tms_views.get_manifest, name="iiif-manifest"),
	path('manifests/<slug:id>/sequence/0', tms_views.get_sequence, name="iiif-manifest-sequence"),
	path('manifests/<slug:id>/canvas/<int:canvas_index>', tms_views.get_canvas, name="iiif-manifest-canvas"),
	path('manifests/<slug:id>/annotation/canvas/<int:canvas_index>', tms_views.get_annotation, name="iiif-manifest-annotation"),

    url(r'^(?P<type>[0-9a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full|allphotos)?/$', tms_views.get_type_html, name='get_type_html'),
    url(r'^v1/(?P<type>[0-9a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full|allphotos)?/$', tms_views.get_type_html_legacy, name='get_type_html_legacy'),
    url(r'^(?P<type>[0-9a-z]+)/(?P<id>[\d]+)\.json$', tms_views.get_type_json, name='get_type_json'),

	url(r'^admin/', admin.site.urls),
]