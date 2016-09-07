from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404

from tms import models
import json

def index(request):
	return render(request, 'tms/index.html')

def get_type_html(request, type, id, view):
	# get site in elasticsearch and render or return 404
	try:
		type_object = models.get_item(id, type)
		print type, id, view
		return render(request, 'tms/'+view+'.html', {'object': type_object, 'type': type})
	except:
		raise Http404("There was an error getting this item")

def get_type_json(request, type, id):
	try:
		type_json = json.dumps(models.get_item(id, type))
		response = HttpResponse(type_json)
		add_headers(response)
		return response
	except:
		raise Http404("There was an error getting this item")

def add_headers(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Content-Type"] = "application/ld+json"
    return response
