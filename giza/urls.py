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
from django.contrib import admin
from tms import views as tms_views
from search import views as search_views

urlpatterns = [
    url(r'^$', tms_views.index, name="index"),
    url(r'^v1/$', tms_views.index_legacy, name="index_legacy"),

    url(r'^(?P<page_name>about|blog|contact|gizacard|news|resources|sampleblog)/$', tms_views.about, name="about"),
    url(r'^v1/(?P<page_name>about|blog|contact|gizacard|news|resources|sampleblog)/$', tms_views.about_legacy, name="about_legacy"),

    url(r'^(?P<page_name>donate)/$', tms_views.donate, name="donate"),
    url(r'^v1/(?P<page_name>donate)/$', tms_views.donate_legacy, name="donate_legacy"),

    url(r'^(?P<page_name>archaeology|commontopics|faq|gizaintro|gizaatschool|giza3d|mygiza-collection|mygiza-saved-searches|mygiza-landing)/$', tms_views.explore, name="explore"),
    url(r'^v1/(?P<page_name>archaeology|commontopics|faq|gizaintro)/$', tms_views.explore_legacy, name="explore_legacy"),

    url(r'^library/$', search_views.library, name="library"),
    url(r'^v1/library/$', search_views.library_legacy, name="library_legacy"),

    url(r'^explorevideos/$', search_views.videos, name="explorevideos"),
    url(r'^v1/explorevideos/$', search_views.videos_legacy, name="explorevideos_legacy"),

    url(r'^search/$', search_views.search, name='search'),
    url(r'^v1/search/$', search_views.search_legacy, name='search_legacy'),

    url(r'^search-results/$', search_views.results, name='results'),
    url(r'^v1/search-results/$', search_views.results_legacy, name='results_legacy'),

    url(r'^(?P<type>[0-9a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full|allphotos)?/$', tms_views.get_type_html, name='get_type_html'),
    url(r'^v1/(?P<type>[0-9a-z]+)/(?P<id>[\d]+)/(?P<view>intro|full|allphotos)?/$', tms_views.get_type_html_legacy, name='get_type_html_legacy'),
    url(r'^(?P<type>[0-9a-z]+)/(?P<id>[\d]+)\.json$', tms_views.get_type_json, name='get_type_json'),

    url(r'^admin/', admin.site.urls),
]
