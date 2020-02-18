from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404

from tms import models
import json

def index_legacy(request):
	return static_pages_legacy(request, 'index')

def about_legacy(request, page_name):
	return static_pages_legacy(request, page_name)

def donate_legacy(request, page_name):
	return static_pages_legacy(request, page_name)

def explore_legacy(request, page_name):
	return static_pages_legacy(request, page_name)

def static_pages_legacy(request, page_name):
	template = 'tms/%s.html' % page_name
	try:
		return render(request, template)
	except:
		raise Http404("This page does not exist!")

def get_type_html_legacy(request, type, id, view):
	# get site in elasticsearch and render or return 404
	# try:
		if view == "intro":
			view = "full"
		type_object = models.get_item(id, type)
		return render(request, 'tms/'+view+'.html', {'object': type_object, 'type': type})
	# except:
	# 	raise Http404("There was an error getting this item")

def get_type_json(request, type, id):
	try:
		type_json = json.dumps(models.get_item(id, type))
		response = HttpResponse(type_json)
		add_headers(response)
		return response
	except:
		raise Http404("There was an error getting this item")



def index(request):
	return render(request, 'pages/index.html')

def about(request, page_name):
	return static_pages_v2(request, page_name)

def donate(request, page_name):
	return static_pages_v2(request, page_name)

def explore(request, page_name):
	return static_pages_v2(request, page_name)

def static_pages(request, page_name):
	template = 'pages/%s.html' % page_name
	try:
		return render(request, template)
	except:
		raise Http404("This page does not exist!")

def get_type_html(request, type, id, view):
	# get site in elasticsearch and render or return 404
	# try:
		if view == "intro":
			view = "full"
		type_object = models.get_item(id, type)
		return render(request, 'pages/'+view+'.html', {'object': type_object, 'type': type})
	# except:
	# 	raise Http404("There was an error getting this item")

def add_headers(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Content-Type"] = "application/ld+json"
    return response
