from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.template.exceptions import TemplateDoesNotExist

from tms import models
from giza.forms import CollectionForm
from utils.elastic_backend import ES_INDEX
import json

def donate_legacy(request, page_name):
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
		type_object = models.get_item(id, type, ES_INDEX)
		return render(request, 'tms/'+view+'.html', {'object': type_object, 'type': type,})
	# except:
	# 	raise Http404("There was an error getting this item")

def get_type_json(request, type, id):
	try:
		type_json = json.dumps(models.get_item(id, type, ES_INDEX))
		response = HttpResponse(type_json)
		add_headers(response)
		return response
	except:
		raise Http404("There was an error getting this item")



def index(request):
	return render(request, 'pages/index.html')

def about(request, page_name):
	return static_pages(request, page_name)

def donate(request, page_name):
	return static_pages(request, page_name)

def explore(request, page_name):
	return static_pages(request, page_name)

def static_pages(request, page_name):
	template = 'pages/%s.html' % page_name
	try:
		return render(request, template)
	except TemplateDoesNotExist:
		raise Http404("This page does not exist!")

def get_type_html(request, type, id, view):
	# get site in elasticsearch and render or return 404
	# try:
	if view == "intro":
		view = "full"
	type_object = models.get_item(id, type, ES_INDEX)

	# add form for creating a new collection in modal
	collection_form = CollectionForm()

	return render(request, 'pages/'+view+'.html', {'object': type_object, 'type': type, 'collection_form': collection_form})
	# except:
	# 	raise Http404("There was an error getting this item")

def add_headers(response):
	response["Access-Control-Allow-Origin"] = "*"
	response["Content-Type"] = "application/ld+json"
	return response


def get_manifest_data(request, id):
	ES_INDEX_IIIF = 'iiif'
	try:
		base_uri = request.build_absolute_uri('/manifests/')
		data = models.get_item(id, "manifest", ES_INDEX_IIIF)
		manifest = data['manifest']
		manifest['@id'] = base_uri + manifest['@id']
		if 'startCanvas' in manifest["sequences"][0]:
			manifest["sequences"][0]['startCanvas'] = base_uri + manifest["sequences"][0]['startCanvas']
		manifest['sequences'][0]['@id'] = base_uri + manifest['sequences'][0]['@id']
		canvases = manifest['sequences'][0]['canvases']
		for canvas in canvases:
			canvas['@id'] = base_uri + canvas['@id']
			for image in canvas['images']:
				image['@id'] = base_uri + image['@id']
				image['on'] = canvas['@id']
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


def get_canvas(request, id, canvas_index):
	manifest = get_manifest_data(request, id)
	if manifest:
		return JsonResponse(manifest['sequences'][0]['canvases'][canvas_index])
	else:
		raise Http404("There was an error getting this manifest")


def get_annotation(request, id, canvas_index):
	manifest = get_manifest_data(request, id)
	if manifest:
		try:
			# so far, there is only one image in the image list
		    annotation = manifest['sequences'][0]['canvases'][canvas_index]['images'][0]
		    return JsonResponse(annotation)
		except:
			raise Http404("There was an error getting this manifest")
	else:
		raise Http404("There was an error getting this manifest")
