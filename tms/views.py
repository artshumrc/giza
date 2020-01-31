from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse

from tms import models
import json

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

	
def get_manifest(request, id, level):
	""" Return json response for manifest found by drs_id """
	try:
		base_uri = request.build_absolute_uri('/manifests/')
		data = models.get_item(id, "iiif_manifest")
		manifest = data['manifest']
		manifest['@id'] = base_uri + manifest['@id']
		manifest['sequences'][0]['@id'] = base_uri + manifest['sequences'][0]['@id']
		manifest['sequences'][0]['canvases'][0]['@id'] = base_uri + manifest['sequences'][0]['canvases'][0]['@id']
		manifest['sequences'][0]['canvases'][0]['images'][0]['@id'] = base_uri + manifest['sequences'][0]['canvases'][0]['images'][0]['@id']
		manifest['sequences'][0]['canvases'][0]['images'][0]['on'] = manifest['sequences'][0]['canvases'][0]['@id']
		if level == 'manifest':
			return JsonResponse(manifest)
		if level == 'sequence':
			return JsonResponse(manifest['sequences'][0])
		if level == 'canvas':
			return JsonResponse(manifest['sequences'][0]['canvases'][0])
		if level == 'annotation':
			return JsonResponse(manifest['sequences'][0]['canvases'][0]['images'][0])
	except:
		raise Http404("There was an error getting this manifest")
