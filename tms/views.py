from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.conf import settings

from tms import models
import json
import os

def index(request):
	return static_pages(request, 'index')

def about(request, page_name):
	return static_pages(request, page_name)

def donate(request, page_name):
	return static_pages(request, page_name)

def explore(request, page_name):
	return static_pages(request, page_name)

def static_pages(request, page_name):
	template = 'tms/%s.html' % page_name
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

def add_headers(response):
	response["Access-Control-Allow-Origin"] = "*"
	response["Content-Type"] = "application/ld+json"
	return response
		

def get_manifest_data(request, id):
	try:
		base_uri = request.build_absolute_uri('/manifests/')
		data = models.get_item(id, "iiif_manifest")
		manifest = data['manifest']
		manifest['@id'] = base_uri + manifest['@id']
		manifest['sequences'][0]['@id'] = base_uri + manifest['sequences'][0]['@id']
		manifest['sequences'][0]['canvases'][0]['@id'] = base_uri + manifest['sequences'][0]['canvases'][0]['@id']
		manifest['sequences'][0]['canvases'][0]['images'][0]['@id'] = base_uri + manifest['sequences'][0]['canvases'][0]['images'][0]['@id']
		manifest['sequences'][0]['canvases'][0]['images'][0]['on'] = manifest['sequences'][0]['canvases'][0]['@id']
		return manifest
	except:
		return None
		

def get_manifest(request, id):
	manifest = get_manifest_data(request, id)
	if manifest:
		response = JsonResponse(manifest)
		response["Access-Control-Allow-Origin"] = "*"
		return response
	else:
		raise Http404("There was an error getting this manifest")


def get_sequence(request, id):
	manifest = get_manifest_data(request, id)
	if manifest:
		return JsonResponse(manifest['sequences'][0])
	else:
		raise Http404("There was an error getting this manifest")
	
	
def get_canvas(request, id):
	manifest = get_manifest_data(request, id)
	if manifest:
		return JsonResponse(manifest['sequences'][0]['canvases'][0])
	else:
		raise Http404("There was an error getting this manifest")
	

def get_annotation(request, id, image):
	manifest = get_manifest_data(request, id)
	if manifest:
		try:
		    annotation = manifest['sequences'][0]['canvases'][0]['images'][image]
		    return JsonResponse(annotation)
		except:
			raise Http404("There was an error getting this manifest")
	else:
		raise Http404("There was an error getting this manifest")
		

# this view if for testing Giza's manifests in mirador, it will be removed	
# def try_mirador(request, id):
# 	data = get_manifest_data(request, id)
# 	return render(request, 'tms/mirador.html', {'data': json.dumps(data)})
