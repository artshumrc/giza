from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404

from tms import models

import json

def site(request, site_id):
	# get site in elasticsearch and render or return 404
	try:
		site = models.get_item(site_id, 'sites')
		return render(request, 'tms/site.html', {'site': site})
	except:
		raise Http404("Site does not exist")

def add_headers(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Content-Type"] = "application/ld+json"
    return response