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
from django.urls import re_path
# from django.urls import path
from django.contrib import admin
from tms import views as tms_views
from search import views as search_views
from . import views

urlpatterns = [
    re_path(r'^$', views.index, name="index"),
    re_path(r'^home', views.home, name="home"),

    re_path(r'^(?P<page_name>blog|gizacard|news|resources|sampleblog)/$', tms_views.about, name="about2"),

    re_path(r'^(?P<page_name>donate)/$', tms_views.donate, name="donate"),

    # re_path(r'^(?P<page_name>giza3d)/$', tms_views.explore, name="explore"),
    re_path(r'^giza-at-school/$', views.giza_at_school, name="giza-at-school"),
    re_path(r'^common-topics/$', views.common_topics, name="common-topics"),
    re_path(r'^faq/$', views.faq, name="faq"),
    re_path(r'^giza-intro/$', views.giza_intro, name="giza-intro"),
    re_path(r'^giza-3d/$', views.giza_3d, name="giza-3d"),
    re_path(r'^giza-3d-model/(?P<mode>[\w-]+)/(?P<id>[\w-]+)/$', views.giza_3d, name="giza-3d-model"),
    re_path(r'^about/$', views.about, name="about"),
    re_path(r'^archaeology/$', views.archaeology, name="archaeology"),
    re_path(r'^contact/$', views.contact, name="contact"),

    re_path(r'^lessons/(?P<slug>[\w-]+)$', views.lesson, name="lesson"),
    re_path(r'^lessons/$', views.lessons, name="lessons"),
    re_path(r'^mygiza/tab/(?P<tab>saved-search-queries|collections|lessons)/$', views.my_giza_tab, name="my-giza-tab"),
    re_path(r'^mygiza/tab/public/$', views.collections_public, name="my-giza-tab-public"),
    re_path(r'^mygiza/tab/private/$', views.collections_private, name="my-giza-tab-private"),
    re_path(r'^mygiza/tab/favorite/$', views.collections_public, name="my-giza-tab-favorite"),
    re_path(r'^mygiza/(?P<tab>saved-search-queries|collections|lessons)/$', views.my_giza, name="my-giza"),
    re_path(r'^mygiza/collections/$', views.collections, name="mygiza-collections-all"),
    # re_path(r'^mygiza/collections/private/$', views.collections_private, name= "mygiza_private_collections"),
    # re_path(r'^mygiza/collections/public/$', views.collections_public, name= "mygiza_public_collections"),
    re_path(r'^mygiza/collections/create/$', views.collections_create, name="mygiza_collections_create"),
    re_path(r'^mygiza/collections/refresh/$', views.collections_all, name="my_giza_collections_refresh"),
    re_path(r'^mygiza/collections/edit/$', views.edit_collection, name="collections_edit"),
    # re_path(r'^collections/(?P<slug>[\w-]+)$', views.collection, name="collection"),
    re_path('mygiza/collections/<uuid:id>/view', views.collections_edit, name="mygiza_collections_view"),
    # re_path(r'^collections/(?P<slug>[\w-]+)/edit$', views.collections_edit, name="collection_edit"),
    # re_path(r'^collections/add', views.collections_add, name="collections_add"),
    re_path(r'^mygiza/collections/add/<slug:slug>', views.collections_add, name="mygiza_collections_add"),
    
    # re_path(r'^collections/edit/<uuid:uuid>', views.collections_edit, name="collection_edit"),
    re_path(r'^collections/all/$', views.collections_all, name="collections"),

    re_path(r'^search/all/update/$', views.search_update, name='search_update'),
    re_path(r'^search/all/del/$', views.search_del, name='search_del'),
    
    # re_path(r'^mygiza/searches/$', views.searches, name="mygiza_searches"),
    re_path(r'^mygiza/searches/all', views.searches_all, name="mygiza_saved_search_queries_all"),
    # re_path(r'^search/all/run/', views.search_run, name="search_run"),
    re_path(r'^search/lookup/$', views.search_token, name='search_token'),
    re_path(r'^my-giza-landing$', views.mygiza, name="my-giza-landing"),
    re_path(r'^search/categories/$', search_views.get_categories, name="search_categories"),
    
    re_path(r'^library/$', search_views.library, name="library"),
    re_path(r'^videos/$', search_views.videos, name="videos"),
    re_path(r'^search/results/$', search_views.search_results, name='search_results'),
    re_path(r'^search/results/add-to-collection$', views.collections_add, name='collections_add'),
    re_path(r'^search/$', search_views.search, name='search'),
    re_path(r'^search/show/$', search_views.search_show, name='search_show'),
    re_path(r'^search/update', search_views.search_results_update, name='search_results_update'),

    # re_path(r'^search/show/$', search_views.searchResultsView.as_view(), name='search_show'),
    re_path(r'^search/save$', views.search_save, name='search_save'),

    # auth
	# TODO for password change/reset, implement django accounts auth
    # path('accounts/', include('django.contrib.auth.urls')),
    re_path('sign-up/', views.sign_up, name='sign-up'),
    re_path('sign-in/', views.sign_in, name='sign-in'),
    re_path('sign-out/', views.sign_out, name='sign-out'),
    re_path('forgot-password/', views.forgot_password, name='forgot-password'),
    re_path(r'^confirm-password/(?P<token>[\w-]+)/$', views.change_password, name="confirm-password"),
    re_path(r'^sign-up-activate/(?P<uidb64>[\w-]+)/(?P<token>[\w-]+)/$', views.activate_account, name="sign-up-activate"),
    re_path(r'^activation-complete/(?P<uidb64>[\w-]+)/(?P<token>[\w-]+)/$', views.activate_account, name="activation-complete"),

    # accounts/password_reset/ [name='password_reset']
    # accounts/password_reset/done/ [name='password_reset_done']
    # accounts/reset/<uidb64>/<token>/ [name='password_reset_confirm']
    # accounts/reset/done/ [name='password_reset_complete']
    # re_path(r'^sign-out/$', RedirectView.as_view(url='/#'), name="sign_out"),

	re_path('manifests/<slug:id>/', tms_views.get_manifest, name="iiif-manifest"),
	re_path('manifests/<slug:id>/sequence/0', tms_views.get_sequence, name="iiif-manifest-sequence"),
	re_path('manifests/<slug:id>/canvas/<int:canvas_index>', tms_views.get_canvas, name="iiif-manifest-canvas"),
	re_path('manifests/<slug:id>/annotation/canvas/<int:canvas_index>', tms_views.get_annotation, name="iiif-manifest-annotation"),

    re_path(r'^(?P<type>[0-9a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full|allphotos)?/$', tms_views.get_type_html, name='get_type_html'),
    re_path(r'^v1/(?P<type>[0-9a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full|allphotos)?/$', tms_views.get_type_html_legacy, name='get_type_html_legacy'),
    re_path(r'^(?P<type>[0-9a-z]+)/(?P<id>[\d]+)\.json$', tms_views.get_type_json, name='get_type_json'),

	re_path(r'^admin/', admin.site.urls),
]