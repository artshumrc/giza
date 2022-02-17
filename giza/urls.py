"""giza URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
	https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
	1. Add an import:  from my_app import views
	2. Add a URL to urlpatterns:  re_path(r'^$', views.home, name='home')
Class-based views
	1. Add an import:  from other_app.views import Home
	2. Add a URL to urlpatterns:  re_path(r'^$', Home.as_view(), name='home')
Including another URLconf
	1. Import the include() function: from django.conf.urls import url, include
	2. Add a URL to urlpatterns:  re_path(r'^blog/', include('blog.urls'))
"""
from django.urls import re_path, path
# from django.urls import path
from django.contrib import admin
from tms import views as tms_views
from search import views as search_views
from . import views

urlpatterns = [

    # DJANGO ADMIN ROUTE
    path('admin/', admin.site.urls),

    # GENERAL PUBLIC ROUTES
    path('home', views.home, name="home"),
    path('library', search_views.library, name="library"),
    path('giza-at-school', views.giza_at_school, name="giza-at-school"),
    path('giza-3d', views.giza_3d, name="giza-3d"),
    path('my-giza-landing', views.mygiza, name="my-giza-landing"),
    path('about', views.about, name="about"),
    path('archaeology', views.archaeology, name="archaeology"),
    path('contact', views.contact, name="contact"),
    path('videos', search_views.videos, name="videos"),
    
    path('common-topics', views.common_topics, name="common-topics"),
    path('faq', views.faq, name="faq"),
    path('giza-intro', views.giza_intro, name="giza-intro"),

    re_path(r'^$', views.index, name="index"),
    
    re_path(r'^giza-3d-model/(?P<mode>[\w-]+)/(?P<id>[\w-]+)/$', views.giza_3d, name="giza-3d-model"),
    re_path(r'^(?P<page_name>blog|gizacard|news|resources|sampleblog)/$', tms_views.about, name="about2"),
    re_path(r'^(?P<page_name>donate)/$', tms_views.donate, name="donate"),

    # LESSONS
    path('lessons', views.lessons, name="lessons"),
    path('lessons/<uuid:pk>', views.lesson, name="lesson"),

    # SEARCH ROUTES
    # path('search/', search_views.search, name='search'),
    path('search/categories/', search_views.get_categories, name="search_categories"),
    path('search/all/update', views.search_update, name='search_update'),
    path('search/del/<uuid:pk>', views.search_del, name='my-giza-del-search'),
    path('search/lookup', views.search_token, name='search_token'),
    path('search/results/', search_views.search_results, name='search_results'),
    # path('search/result/<str:form>', views.get_form, name='get-form'),
    path('search/result/get_form/<str:form>/<str:type>/<int:id>/', views.get_form, name='get-form'),
    re_path(r'^/<str:tab>/<str:type>/<int:id>/', views.my_giza_add, name='add-to-my-giza-collection'),
    path('search/result/<str:tab>/<str:type>/<int:id>/<str:name>/', views.my_giza_add, name='add-to-my-giza-collection'),
    # path('search/result/<str:type>/<int:id>/<uuid:collection>', views.collections_add, name="mygiza_collections_add"),
    # path('search/results/add-to-collection', views.collections_add, name='my-giza-add-to-collection'),
    path('search/show', search_views.search_show, name='search_show'),
    path('search/update', search_views.search_results_update, name='search_results_update'),

    re_path(r'^search/result/(?P<type>[0-9a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full|allphotos)?/$', search_views.get_type_html, name='get_type_html'),

    # MY GIZA PATHS
    path('mygiza/tab/public', views.collections_public, name="my-giza-tab-public"),
    path('mygiza/tab/private', views.collections_private, name="my-giza-tab-private"),
    path('mygiza/tab/favorite', views.collections_public, name="my-giza-tab-favorite"),
    path('my-giza/save/search', views.search_save, name='my-giza-save-search'),
    path('mygiza/collections/all', views.collections, name="my-giza-collections-all"),
    path('mygiza/collections/refresh', views.collections_all, name="my_giza_collections_refresh"),
    path('mygiza/collections/<uuid:token>/delete', views.collections_delete, name="my-giza-collections-delete"),
    path('mygiza/collections/<uuid:token>/edit', views.edit_collection, name="my-giza-collections-edit"),
    path('mygiza/collections/<uuid:id>/view', views.collections_edit, name="mygiza_collections_view"),
    path('mygiza/get_collections', views.collections, name="mygiza-get-collections"),
    
    # re_path(r'^mygiza/tab/(?P<tab>saved-search-queries|collections|lessons)/$', views.my_giza_tab, name="my-giza-tab"),
    re_path(r'^mygiza/(?P<tab>saved-search-queries|collections|lessons)/$', views.my_giza, name="my-giza"),
    path('mygiza/collections/add/<str:tab>', views.my_giza_add, name="my-giza-add"),
    re_path(r'^mygiza/searches/all', views.searches_all, name="mygiza_saved_search_queries_all"),
    re_path(r'^collections/all/$', views.collections_all, name="collections"),   

    # SIGN UP/IN/OUT ROUTES
    path('sign-up', views.sign_up, name='sign-up'),
    path('sign-in', views.sign_in, name='sign-in'),
    path('sign-out', views.sign_out, name='sign-out'),
    path('forgot-password', views.forgot_password, name='forgot-password'),
    re_path(r'^confirm-password/(?P<token>[\w-]+)/$', views.change_password, name="confirm-password"),
    re_path(r'^sign-up-activate/(?P<uidb64>[\w-]+)/(?P<token>[\w-]+)/$', views.activate_account, name="sign-up-activate"),
    re_path(r'^activation-complete/(?P<uidb64>[\w-]+)/(?P<token>[\w-]+)/$', views.activate_account, name="activation-complete"),

    # MIRADOR MANIFEST ROUTES
	path('search/results/manifests/<str:type>/<int:id>/', tms_views.get_manifest, name="iiif-manifest"),
	path('manifests/<slug:id>/sequence/0', tms_views.get_sequence, name="iiif-manifest-sequence"),
	path('manifests/<slug:id>/canvas/<int:canvas_index>', tms_views.get_canvas, name="iiif-manifest-canvas"),
	path('manifests/<slug:id>/annotation/canvas/<int:canvas_index>', tms_views.get_annotation, name="iiif-manifest-annotation"),

    # UNKNOWN~POTENTIALLY NOT LONGER IN USE
    re_path(r'^v1/(?P<type>[0-9a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full|allphotos)?/$', tms_views.get_type_html_legacy, name='get_type_html_legacy'),
    re_path(r'^(?P<type>[0-9a-z]+)/(?P<id>[\d]+)\.json$', tms_views.get_type_json, name='get_type_json'),
    # re_path(r'^mygiza/collections/private/$', views.collections_private, name= "mygiza_private_collections"),
    # re_path(r'^mygiza/collections/public/$', views.collections_public, name= "mygiza_public_collections"),
    # re_path(r'^mygiza/collections/add/(?P<tab>saved-search-queries|collections|lessons)/$', views.my_giza_add, name="add-to-my-giza-collection"),
    # re_path(r'^collections/(?P<slug>[\w-]+)$', views.collection, name="collection"),
    # re_path(r'^collections/(?P<slug>[\w-]+)/edit$', views.collections_edit, name="collection_edit"),
    # re_path(r'^collections/add', views.collections_add, name="collections_add"),
    # re_path(r'^collections/edit/<uuid:uuid>', views.collections_edit, name="collection_edit"),
    # re_path(r'^mygiza/searches/$', views.searches, name="mygiza_searches"),
    # re_path(r'^search/all/run/', views.search_run, name="search_run"),
    # re_path(r'^search/show/$', search_views.searchResultsView.as_view(), name='search_show'),
    # re_path(r'^(?P<page_name>giza3d)/$', tms_views.explore, name="explore"),
]