from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404

from tms import models
from utils.views_utils import RELATED_DISPLAY_TEXT
import json

def index(request):
	return render(request, 'tms/index.html')

def get_type_html(request, type, id):
	# get site in elasticsearch and render or return 404
	try:
		type_object = models.get_item(id, type)
		print type, id
		return render(request, 'tms/'+type+'.html', {'object': type_object})
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

def get_type_related_items(request, type, id, relation):
	# get site's related items in elasticsearch and render or return 404
	try:
		print type, id, relation
		type_object = models.get_item(id, type)
		related_items = type_object['relateditems'][relation]
		print RELATED_DISPLAY_TEXT[relation]
		return render(request, 'tms/'+type+'_related.html', {'relateditems': related_items, 
			'displaytext' : RELATED_DISPLAY_TEXT[relation],
			'relation' : relation })
	except:
		raise Http404("There was an error getting this item")

def add_headers(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Content-Type"] = "application/ld+json"
    return response