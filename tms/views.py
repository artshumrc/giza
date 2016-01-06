from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404

from tms import models

import json

related_display_text = {
	'finds' : 'Finds', 
	'diarypages' : 'Diary Pages', 
	'modernpeople' : 'Modern People', 
	'ancientpeople' : 'Ancient People',
	'plansanddrawings' : 'Plans and Drawings',
	'unpublisheddocuments' : 'Unpublished Documents',
	'publisheddocuments' : 'Published Documents',
	'photos' : 'Photos'
}

def site(request, id):
	# get site in elasticsearch and render or return 404
	try:
		site = models.get_item(id, 'sites')
		return render(request, 'tms/site.html', {'site': site})
	except:
		raise Http404("Site does not exist")

def site_related_items(request, id, relation):
	# get site's related items in elasticsearch and render or return 404
	try:
		site = models.get_item(id, 'sites')
		related_items = site['relateditems'][relation]
		return render(request, 'tms/site_related.html', {'relateditems': related_items, 
			'displaytext' : related_display_text[relation],
			'relation' : relation })
	except:
		raise Http404("Site does not exist")

def find(request, id):
	try:
		find = models.get_item(id, 'finds')
		return render(request, 'tms/find.html', {'find': find})
	except:
		raise Http404("Find does not exist")

def find_related_items(request, id, relation):
	# get find's related items in elasticsearch and render or return 404
	try:
		find = models.get_item(id, 'finds')
		print find
		print relation
		related_items = find['relateditems'][relation]
		return render(request, 'tms/find_related.html', {'relateditems': related_items, 
			'displaytext' : related_display_text[relation],
			'relation' : relation })
	except:
		raise Http404("Find does not exist")

def diarypage(request, id):
	return

def diarypage_related_items(request, id, relation):
	return

def ancientperson(request, id):
	return

def ancientperson_related_items(request, id, relation):
	return

def modernperson(request, id):
	return

def modernperson_related_items(request, id, relation):
	return

def photo(request, id):
	return

def photo_related_items(request, id, relation):
	return

def plansanddrawings(request, id):
	try:
		plansanddrawings = models.get_item(id, 'plansanddrawings')
		return render(request, 'tms/plansanddrawings.html', {'plansanddrawings': plansanddrawings})
	except:
		raise Http404("Plan and Drawing does not exist")

def plansanddrawings_related_items(request, id, relation):
	return

def publisheddocument(request, id):
	return

def publisheddocument_related_items(request, id, relation):
	return

def unpublisheddocument(request, id):
	try:
		unpublisheddocument = models.get_item(id, 'unpublisheddocuments')
		return render(request, 'tms/unpublisheddocument.html', {'unpublisheddocument': unpublisheddocument})
	except:
		raise Http404("Unpublished Document does not exist")

def unpublisheddocument_related_items(request, id, relation):
	return

def add_headers(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Content-Type"] = "application/ld+json"
    return response