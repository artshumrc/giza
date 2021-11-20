from django.http.response import HttpResponse, JsonResponse
from django.template.loader import render_to_string, get_template
from django.views.generic import TemplateView
from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
import copy, re, operator, inspect, json
from operator import getitem
from functools import reduce
import collections

import os


from dateutil.parser import parser
from datetime import *

from utils.elastic_backend import es, ES_INDEX, scan
from utils.views_utils import CATEGORIES, FACETS_PER_CATEGORY, FIELDS_PER_CATEGORY, MET_SIMPLE, MET_SIMPLE_REVERSED, MONTHS

RESULTS_SIZE = 20


####################################
### 		HELPER FUNCTIONS	 ###
####################################
def timit():
	return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]





####################################
###				ROUTES			 ###
####################################
def search(request):
	return render(request, 'pages/search.html')

def search_show(request):
	return render(request, 'pages/searchresults.html')
	




####################################
###				LIBRARY			 ###
####################################
# get all pubdocs with pdfs for Digital Giza Library
def library(request):
	sort = request.GET.get('sort', 'name')
	if sort == 'name':
		results = es.search(index=ES_INDEX, doc_type='library', body={
			"size": 500,
			"sort": "sort"+sort,
			"query": {
				"match_all" : {}
			}
		})['hits']['hits']
		current_letter = 'a'
		hits = []
		letter_docs = {}
		letter_docs[current_letter] = []
		for r in results:
			source = r['_source']
			if source['name'].lower().startswith(current_letter):
				letter_docs[current_letter].append(source)
			else:
				hits.append(letter_docs)
				current_letter = source['name'].lower()[0]
				letter_docs = {}
				letter_docs[current_letter] = []
				letter_docs[current_letter].append(source)
		hits.append(letter_docs)
	else:
		# year, format - TODO: title
		results = es.search(index=ES_INDEX, doc_type='pubdocs', body={
		   "size": 0,
		   "query": {
				"match_all": {}
		   },
		   "aggs": {
			  "by_sort": {
				 "terms": {
					"field": sort+".keyword",
					"order": {
					   "_term": "asc"
					},
					"size": 500
				 },
				 "aggs": {
					"by_top_hit": {
					   "top_hits": {
						  "size": 100
					   }
					}
				 }
			  }
		   }
		})['aggregations']['by_sort']['buckets']
		hits = []
		for r in results:
			sort_docs = {}
			key = r['key']
			sort_docs[key] = []
			docs = []
			sort_docs[key].append({'docs' : docs})
			for h in r['by_top_hit']['hits']['hits']:
				if ('pdf' in h['_source'] and h['_source']['pdf'] != ''):
					docs.append({
					'url' : h['_source']['pdf'],
					'displaytext' : h['_source']['boilertext'],
					'format' : h['_source']['format']
					})
			if len(docs) > 0:
				hits.append(sort_docs)

	return render(request, 'pages/library.html', {
		'results' : hits,
		'sort' : sort
	})
	




####################################
###			TOUR VIDEOS			 ###
####################################
# get virtual Giza tour videos
def videos(request):
	results = es.search(index=ES_INDEX, doc_type='videos', body={
		"size": 500,
		"query": {
			"wildcard" : {
				"number" : "gph_3dp*"
			}
		},
		"sort" : "displaytext.keyword"
	})['hits']['hits']
	hits = []
	for r in results:
		hits.append(r['_source'])
	return render(request, 'pages/videos.html', {
		'results' : hits
	})
	




####################################
###				MET				 ###
####################################
def MET_lookup(term=None, code=None):
	"""
	This method returns either the MET code or term corresponding to the input.
	### Parameters
	- term : str
		- A term to look for.
	- code : str
		- Three uppercase alpha chars separated by a dot

	"""
	if code:
		return MET_SIMPLE[code].title()
	elif term:
		return MET_SIMPLE_REVERSED[term.lower()].upper()
	else:
		return False

def MET_path(term=None, code=None):
	"""
	This method returns a path based on an MET code or term
	### Parameters
	- term : str
		- A term to look for.
	- code : str
		- Three uppercase alpha chars separated by a dot
	"""
	path = []
	if code:
		c = code.split('.')
		while c:
			res = MET_lookup(code=code)
			if res:
				path.append(res)
			c.pop()
			code = ".".join(c)

		return path[::-1]
	
	if term:
		return MET_path(code=MET_lookup(term=term))

def build_MET(buckets):
	"""
	This method aggregates all MET values into a dictionary to be sent back to the client. The MET values are currently
	dependent on selected category only. NOTE: ES limits document retrieval to 10000. This is untested for search queries that result 
	in more than 10,000 MET terms. In that case ES would limit the output to 10,000 on MET_paths. One possible workaround is to use 
	the ES scrolling API, but this may provide additional waiting time for the user in case of processing large search batches.
	"""
	if 'aggregations' in buckets:
		MET_aggregations = { k : v for k, v in buckets['aggregations'].items() if 'MET_code' in k or 'MET_path' in k }
		if len(MET_aggregations):
			# for facet_category, v in MET_aggregations.items():
			codes = { x['key'] : x['doc_count'] for x in MET_aggregations['MET_code']['buckets'] }
			doc_counts = { x['key'] : x['doc_count'] for x in MET_aggregations['MET_paths']['buckets'] }
			if len(codes) and len(doc_counts):
				allCodes = {}

				# This private method collects the full path (code) to each term. 
				# For example: 
				# 	-	AAA_AAA_AAB requires [AAA, AAA_AAA]
				# 	-	AAA_AAB_AAF_AAB requires [AAA, AAA_AAB, AAA_AAB_AAF]
				def checkCode():
					for k, v in codes.items():
						fullCodes = getCodes(k.split('_')[:-1])
						for code in fullCodes:
							if code is not '' and code not in allCodes:
								allCodes[code] = 0
								# checkCode()
						if k not in allCodes:
							allCodes[k] = v
				
				checkCode()

				combined = [{ 
						'Code' : k,
						'Term' : MET_lookup(code=k), 
						'Level' : len(k.split('_')),
						'Doc_count' : doc_counts[MET_lookup(code=k).lower()] if MET_lookup(code=k).lower() in doc_counts else 0
					}
					for k in allCodes.keys()
				]

				def get_by_path(root, items):
					return reduce(operator.getitem, items, root)

				def set_by_path(root, items, value):
					get_by_path(root, items[:-1])[items[-1]] = { 
						'key' : value[0], 
						'count' : value[1],
						'path' : "_".join(items)
					}
			
				di = {}

				# BUILD RECURSIVE TREE FOR TEMPLATE
				[set_by_path(di, x['Code'].split('_'), (x['Term'], x['Doc_count'])) for x in combined]
				
				# SORT THE TREE FOR ALPHABETIC RENDERING ON TEMPLATE
				return sorted(di.items(), key=lambda k: operator.getitem(k[1], 'key'))
	return {}

def getCodes(code):
	return ["_".join(code[:idx+1]) if len(code) > 1 else "".join(code[:idx+1]) for idx, c in enumerate(code) ]
	
def red(a, b):
	cat, name = b.split('_')
	a[cat] = { name : b.value }
	return a

####################################
###			SEARCH ROUTES		 ###
####################################
def search_results(request):
	""" This route passes the Django Request object on to the base parameters method and will receive the items dictionary.
	It then renders the initial search_results page with items and returns the HTML to the user.
	###Parameters
	- request : Django request object
		- The request sent from the client to the server
	###Returns
	- Render function with template
	"""
	items = __prepare_base_params(request)
	return render(request, 'pages/search-results.html', {
		'MET_tree' : items['search']['MET']['MET_tree'],
		# 'MET_paths' : items['search']['MET']['MET_paths'],
		'search': items['search'],
		'result' : items['search']['result'],
		'facets' : items['search']['facets'],
	})

@csrf_exempt
def search_update(request):
	""" This route reprocesses the new search parameters that are sent from the frontend through an AJAX post request.
	The method first calls __prepare_base_params, which is detailed below and will result in a new items global object, which 
	forms the basis to recompile the various templates required on the frontend.
	###Parameters
	-	request : Django Request Object
		- The Django Request object sent through AJAX on the frontend
	"""
	items = __prepare_base_params(request)
	return JsonResponse({ 
		'search_stats' : render_to_string('search-stats.html', { 'search': items['search'] }), 
		'search_result' : render_to_string('search-result.html', { 'result': items['search']['result'] }), 
		'search_facets' : render_to_string('search-facets.html', { 'facets': items['search']['facets'] }), 
		'search_params' : render_to_string('search-params.html', { 'fields': items['search']['fields'] }), 
		'search_pagination' : render_to_string('search-pagination.html', { 'result': items['search']['result'] }),
		'search_categories' : render_to_string('search-categories.html', { 'search' : items['search'] }),
		'search_MET' : render_to_string('search-MET.html', { 'MET_tree': items['search']['MET']['MET_tree'] }),
		'search' : items['search']
	})

####################################
###			SEARCH ROUTES		 ###
####################################
def __prepare_base_params(request):
	"""
	This method prepares the base parameters for every search called. The method takes in the Django Request object
	to extract all fields 
	###Output
	- dict
		- A dictionary with fields:
			- query : str, search query if query is entered in the simple search box (header.html).
			- category : str, overall category of search from the advanced search form (search-advanced.html).
			- fields : dict, search fields from the advanced search form (search-advanced.html).
			- results : dict, results returned from the search parameters. This includes all aggregated facets as well.
			- categories : dict, categories represented in the data set.
			- facets: dict, facets in the data set, including selected and unselected.
			
	"""
	#########################
	#		BASE PARAMS		#
	#########################
	items = {'search' : {} }
	
	# IF A SEARCH IS SUBMITTED FOR THE FIRST TIME
	if not 'search' in request.POST:
		items['search']['fields'] = list(request.POST.items())

		# REFORMAT SEARCH PARAMETERS FROM ADVANCED SEARCH FORM
		items['search']['fields'] = { x[0].split('_')[0] : {} if '_' in x[0] else (json.loads(x[1]) if '{' in x[1] else x[1]) for x in list(request.POST.items()) }
		{ items['search']['fields'][x].update({ y[0].split('_')[1] : y[1] }) for x in items['search']['fields'] for y in list(request.POST.items()) if x == y[0].split('_')[0] and type(items['search']['fields'][x]) is dict}
		items['search']['category'] = items['search']['fields']['category']
		del items['search']['fields']['category']
		items['search']['fields'] = { y : z for k, v in { k : v for k, v in items['search']['fields'].items() if isinstance(v, dict) }.items() for y, z in v.items() if z is not ''}

		# ADD QUERY IF ANY
		items['search']['query'] = request.POST.get('query') if request.POST.get('query') else ""
		
		# ADD MET
		items['search']['MET'] = request.POST.get('MET') if request.POST.get('MET') else { 'MET_tree' : {}, 'MET_paths' : [] }

		# FACETS
		items['search']['facets'] = {}
		
		# EXTRACT FIELDS THAT WERE SEARCHED FOR
		items['search']['result'] = { 'hits' : [], 'total' : 20, 'params' : [ { y : z } for k, v in { k : v for k, v in items['search']['fields'].items() if isinstance(v, dict) }.items() for y, z in v.items() if z is not ''] }

		# ADD STARTING PAGE
		items['search']['result']['pages'] = { 'page' : 1 }
	else:

		# IF SEARCH PARAMETERS ALREADY EXIST IN THE REQUEST POST
		items['search'] = json.loads(request.POST.get('search'))

	# IF REQUEST OBJECT IS FROM REDEEMING A SEARCH TOKEN
	# if token:
	# 	items = token[0]
	# 	del items['key']
	# 	if 'fields' in items:
	# 		items.update({ f'{items["category"][0]}_{k}' : v['val'] for k, v in items['fields'].items() })
	# 		del items['fields']
	
	#########################
	#	SIMPLE SEARCH		#
	#########################
	# USER DID NOT PROVIDE A SEARCH QUERY
	# if len(items['query']) == 0 and  not in search_terms and 'category' not in search_terms:
	# 	search_results = es.search(
	# 		index=ES_INDEX,
	# 		size=RESULTS_SIZE,
	# 		body={
	# 			"query" : { "match_all" : {} },
	# 			"sort" : [ 
	# 				{ "_uid" : "asc" } 
	# 				],
	# 			},
	# 		scroll='5m')
	
	# USER PROVIDED A SEARCH QUERY WITH COLON AND MAY BE LOOKING FOR A SPECIFIC OBJECT (E.G.: 'objects:HUMFA_27-5-1')
	if ':' in items['search']['query']:
		print('specific object search')
		# parts = search_terms['term'].split(':')
		# if parts[0] in CATEGORIES:
		# 	search_results = es.search(index=ES_INDEX, doc_type=parts[0], body={"query" : { "match" : { "allnumbers" : { parts[1] } } } })
			
		# 	# ONE RESULT WILL IMMEDIATELY DIRECT TO RESULT PAGE
		# 	if search_results['hits']['total'] == 1:
		# 		return HttpResponseRedirect(reverse('get_type_html', args=(parts[0], search_results['hits']['hits'][0].get('_source').get('id'), 'full')))
		# 	else:
		# 		print(f'Unique number search at {inspect.getframeinfo(inspect.currentframe()).lineno} resulted in more than one record')
		# 		# STOP-MEASURE: RETURN ALL OR NO RESULTS
		# 		for hit in search_results['hits']['hits']:
		# 			hits.append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})

	#########################
	#	ADVANCED SEARCH		#
	#########################

	# USER DID A SIMPLE OR ADVANCED SEARCH
	else:

		# SEARCH CATEGORY IS SPECIFIED
		if items['search']['category']:

			# CHECK IF USER IS SEARCHING FOR DATE OR DATE RANGE
			for (key, value) in items['search']['fields'].items():
				if 'date' in key and value is not '': 
					res = chkDate(value)
					if res[0]:
						items['search']['fields'][f'{key}_ms'] = {}
						items['search']['fields'][f'{key}_ms'] = [int(x[1]) for x in res[1]]
	
	#########################
	#	PROCESS SEARCH Q	#
	#########################
	items['search'], search_results = search_execute(items['search'])

	#########################
	#		SEPARATE	 	#
	#########################
	items['search']['categories'] = [ { 'displaytext' : CATEGORIES[x['key']], 'key' : x['key'], 'doc_count' : x['doc_count'] } for x in search_results['aggregations']['doc_types']['buckets']]
	del search_results['aggregations']['doc_types']

	#########################
	#		COMPILE MET 	#
	#########################
	items['search']['MET']['MET_tree'] = build_MET(search_results)
	# WHEN INCLUDING AN MET TERM:
		# FILTER CURRENT RESULTS

	# SURFACE FACETS IN ITEMS, BUT PRESERVES TRUTHY FLAG IF SET
	selected_facets = []
	if items['search']['facets']:
		selected_facets = list(find_val(items['search']['facets'], True))
	items['search']['facets'] = { k : v for x in __recurse_aggs('', search_results, [], selected_facets) for k, v in x.items() }
	# if not len(items['search']['facets']['unselected']):
		# items['search']['facets']['unselected'] = { k : v for x in __recurse_aggs('', search_results, [], []) for k, v in x.items() }

	# if not all(x in FACETS_PER_CATEGORY[items['search']['category']] for x in list(items['search']['facets']['unselected'].keys())) and all(x in FACETS_PER_CATEGORY[items['search']['category']] for x in list(items['search']['facets']['selected'].keys())):
		# items['search']['facets']['unselected'] = { k : v for x in __recurse_aggs('', search_results, [], []) for k, v in x.items() }
	
	# GET THE NEXT PAGE OF RESULTS
	
	# THE QUERY SEND TO ELASTICSEARCH TO FIND ITEMS TO SHOW
	# search_results = es.search(index=ES_INDEX, body={
	# 	"from": results_from,
	# 	"size": RESULTS_SIZE,
	# 	"query": base_query,
	# 	"aggregations": {
	# 		"aggregation": {
	# 			"terms": {
	# 				"field": "_type",
	# 				"exclude": "library", # ignore special type, library, which is used for the Digital Giza Library page
	# 				"size" : 50 # make sure to get all categories (rather than just 10)
	# 			}
	# 		}
	# 	},
	# 	"post_filter" : {
	# 		"bool" : bool_filter
	# 	},
	# 	"sort" : request.POST.get('sort', '_score')
	# 	}
	# )

	# APPEND THE TWENTY SEARCH RESULTS FOR DISPLAY
	items['search']['result']['total'] = search_results['hits']['total'] if search_results['hits']['total'] <= 10000 else 10000
	items['search']['result']['hits'] = [{ 'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source') } for hit in search_results['hits']['hits']]
	# for hit in search_results['hits']['hits']:
		# items['search']['result'].append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})
		# if 'MET_path' in hit.get('_source'):
			# MET_paths.append({ 'id' : hit.get('_id'), 'MET_path' : hit.get('_source')['MET_path'] })

	items['search']['result']['pages'].update(page_results(items['search']))

	del items['search']['base']
	del items['search']['bool']
	del items['search']['aggs']

	return items

####################################
###			QUERY BUILDING		 ###
####################################
def search_execute(items):
	""" This function calls all methods to construct and execute the search query
	Once the query has been constructed from __build_es_query, __build_bool, and __build_aggregations
	the method returns the ElasticSearch query results.
	"""
	items = __build_es_query(items) 		# BUILD NORMAL BASE JSON QUERY
	items = __build_bool(items) 			# BUILD BOOLEAN FILTERS
	items = __build_aggregations(items)		# AGGREGATE RELATED CATEGORIES AND FACETS
	
	addToClipBoard(json.dumps(__body_query(items)))		# DEBUGGING ELASTICSEARCH QUERY
	
	return items, __search_get_results(__body_query(items))

def __search_get_results(query):
	""" This private function executes the query to collect all search results from ES.
	These results include all aggregated results, MET, facets and otherwise.
	"""
	return es.search(index=ES_INDEX, body=query)

def __build_es_query(items):
	""" This private method builds the ElasticSearch base query. This method does nothing with facets or ...
	###Parameters
	- items : dict
		- A dictionary with all search_terms
	###Output
	- An updated dictionary with all search_terms and bool_filter field
	"""
	items['base'] = {}
	should, must = [], []

	# IF NO SEARCH TERM OR FIELDS ARE PROVIDED RETURN EVERYTHING IN DATABASE
	if not len(items['query']) and not len(items['category']):
		items['base'] = { "match_all" : {}}

	# CONSTRUCT A SHOULD-QUERY IF QUERY TERM IS PROVIDED (SIMPLE SEARCH)
	if len(items['query']):
		should.append({ "match" : { "_all" : { "query" : items['query'] } } })

	# CONSTRUCT A MUST-QUERY IF A CATEGORY IS SPECIFIED (ADVANCED SEARCH)
	if items['category']:
		for k, v in items['fields'].items():
			if len(v):
				
				# RANGE MATCH IF THE SEARCH IS FOR A DATE (IN MILLISECONDS)
				if '_ms' in k and len(v):
					must.append({ "match" : { k : v[0] } }) if len(v) == 1 else must.append({ "range" : { k : { "gte" : v[0], "lte" : v[1] } } })
				else:
					must.append({ "match" : { k : { "query" : v } } })
		
	items['base'] = { "must" : must, "should" : should }

	return items

def __build_bool(items):
	""" This private method builds a ElasticSearch bool filter. The bool filter will be appended to the ElasticSearch query
	and filters 
	###Parameters
	- params : dict
		- A dictionary with all search_terms
	###Output
	- A dictionary with all bool filters
	"""
	# strucure should be at the top level a must bool
	# each facet type is a should bool with all selected values in the array
	# the should bool is an item in the must bool array
	# current_category is in item in the must bool array

	items['bool'] = {}
	must, should = [], []

	# GET DOCUMENT TYPES
	if items['category']:
		must.append({
			"type" : {
				"value" : items['category']
			}
		})

	# IF THERE ARE MET TERMS
	if len(items['MET']['MET_paths']):
		for v in items['MET']['MET_paths']:
			should.append({ "match" : { "MET_path_CN" : v } })

	# IF THERE ARE FACETS
	if len(items['facets']):

		# PROCESS ALL SELECTED FACETS
		for facet_category, facets in items['facets'].items():
			for facet in facets:
				if facet_category in FACETS_PER_CATEGORY[items['category']] and facet['selected']:
					field = list(find_key('field', FACETS_PER_CATEGORY[items['category']][facet_category]))[0]
					if 'nested' in FACETS_PER_CATEGORY[items['category']][facet_category]:
						path = FACETS_PER_CATEGORY[items['category']][facet_category]['nested']['path']
						should.append({
							"nested": {
								"path": path,
								"query" : { 
									"term": {
										field : facet['display_text']
									}
								}
							}
						})
					else:
						should.append({ "term": { field : facet['display_text'] }})

	must.append({"bool" : { "should" : should }})

	# ASSIGNING THE FILTER ON THE ITEMS DICTIONARY TO BE PROCESSED IN THE QUERY
	items['bool'] = { "must" : must }
	
	return items

def __build_aggregations(items):
	"""
	This method builds the aggregation dictionaries to append to the query. There are two types of aggregations that are
	being processed. The first is to retrieve all document types related to the query, for example, photos, 3D models etc.
	The second type of aggregation is that of all facets related to the query.
	###Parameters
	- params : dict
		- Search parameters that are being passed back and forth between frontend and backend
	###Output
		- The filter that is appended to the ES base query
	"""
	items['aggs'] = {}

		# 	"aggregations": {
	# 		"aggregation": {
	# 			"terms": {
	# 				"field": "_type",
	# 				"exclude": "library", # ignore special type, library, which is used for the Digital Giza Library page
	# 				"size" : 50 # make sure to get all categories (rather than just 10)
	# 			}
	# 		}
	# 	},
	# 	"post_filter" : {
	# 		"bool" : bool_filter
	# 	},
	# 	"sort" : request.POST.get('sort', '_score')
	# 	}

	# SIMPLE SEARCH USE-CASE
	if not items['category']:
		return items
	else:
		
		# AGGREGATE ALL FACETS REGISTERED FOR THE CURRENT DOCUMENT TYPE
		aggs = { name : term_agg for name, term_agg in list(FACETS_PER_CATEGORY[items['category']].items()) }

		# AGGREGATE ALL MET TERMS IN THE AGGREGATED DATA SET
		# THIS SHOULD TAKE AGGREGATED FACETS INTO ACCOUNT ^^
		# aggs
		# aggs['paths'] = { "terms" : { "field" : "MET_path_CN.Path.keyword", "size" : 10000 }}
		# aggs['code'] = { "terms" : { "field" : "MET_path_CN.Code.keyword", "size" : 10000 }}
		
		# AGGREGATE ALL DATA TYPES IN THE DATA SET
		aggs['doc_types'] = { 
			'terms' : {
				'field' : '_type',
				'exclude' : 'library',
				'size' : 50
			}
		}
		items['aggs'] = aggs
		return items

	# DOESN'T ARRIVE AT THIS CODE: DOES NOT INCLUDE ALL FACETS IN THE SEARCH QUERY

	METpaths = { "terms" : {"field" : "MET_path_CN.Path.keyword", "size" : 10000 }}
	METcode = { "terms" : { "field" : "MET_path_CN.Code.keyword", "size" : 10000 }}

	aggregations = {}
	# # aggs_for_selected = {}
	aggs_for_unselected = {}
	# should = []
	# aggregations for a facet that has been selected by the user will only be affected by other selected facets

	for name, term_agg in list(FACETS_PER_CATEGORY[items['category']].items()):
		if items['category'] in items['facets']['selected'] and name in items['facets']['selected'][items['category']]:
			bool_filter_for_facet = __build_bool(items, name)
			filter_name = name + "_selected_filter"
			aggregations[filter_name] = {
				"filter" : {
					"bool" : bool_filter_for_facet
				},
				"aggregations": {
					name : term_agg,
				}
			}
			aggregations['paths'] = METpaths
			aggregations['code'] = METcode
		else:
			# other aggregations will be filtered by the selected facets
			aggs_for_unselected[name] = term_agg

	# filter_name = "_".join(list(params['search_params']['facets'][params['search_params']['category']].keys())) + "_filter"

	# aggregations[filter_name] = {
	# 	"filter" : {
	# 		"bool" : items['bool']
	# 	},
	# 	"aggregations": aggs_for_unselected
	# }

	items['aggs'][f'{items["category"]}_filter'] = {
		"filter" : {
			"bool" : items['bool']
		},
		"aggregations": aggs_for_unselected
	}

	return items

def __body_query(items):
	"""
	This method builds the body of the query that is sent to ElasticSearch.
	We assume that the user is requesting a baseline query, i.e. doing a simple search and wants all results.
	We are looking to return results starting at 0. We implement the scroll API to retrieve datasets larger than
	10,000 results
	"""
	return {
		'from' : (items['result']['pages']['page'] - 1) * RESULTS_SIZE,
		'size' : RESULTS_SIZE if (items['result']['pages']['page'] - 1) * RESULTS_SIZE + RESULTS_SIZE < items['result']['total'] else (items['result']['total'] - (items['result']['pages']['page'] - 1) * RESULTS_SIZE),
		"query" : { "bool" : items['base'] },
		"aggregations" : items['aggs'],
		"post_filter" : { "bool" : items['bool'] },
		"sort" : '_score'
	}
####################################





####################################
###		CONVENIENCE METHODS		 ###
####################################
def __recurse_aggs(agg_name, search_results, facets, selected_facets):
	"""
	This method iterates through the different levels of the search results to bring all aggregations to the same top-level and 
	is called after the search has been returned from ElasticSearch. Some aggregated data comes from nested fields 
	(see __build_subfacet_aggs) and are therefore deeper in the record (see the CATEGORIES variable).
	###Parameters
	- agg_name : str
		-
	- search_results : dict
		-
	- facets :
		-
	- selected_facets : list of dict
		-
	"""
	if type(search_results) != type(dict()):
		return facets

	if 'aggregations' not in search_results:
		facet_array = []
		if 'buckets' in search_results:
			for bucket in search_results['buckets']:
				if bucket['key'] and bucket['doc_count']:
					agg = { 
						'display_text' : bucket['key'],
						'doc_count' : bucket['doc_count'],
						'selected' : True if any([x for x in selected_facets for y in x.values() if y == bucket['key']]) else False
					}
					facet_array.append(agg)
			if agg_name in selected_facets:
				facets.insert(0, { agg_name : facet_array })
			else:
				facets.append({ agg_name : facet_array })
			return facets
		else:
			for agg_name, value in list(search_results.items()):
				__recurse_aggs(agg_name, value, facets, selected_facets)
			return facets
	else:
		for agg_name, value in list(search_results['aggregations'].items()):
			if agg_name != 'code' and agg_name != 'paths':
				__recurse_aggs(agg_name, value, facets, selected_facets)
		return facets

def find_key(key, value):
	for k, v in value.items():
		if k == key: yield v
		elif isinstance(v, dict):
			for result in find_key(key, v):
				yield result
		elif isinstance(v, list):
			for d in v:
				for result in find_key(key, d):
					yield result

def find_val(data, value):
	if isinstance(data, dict):
		for k, v in data.items():
			if v == value and isinstance(v, bool): yield v
			else: 
				yield from find_val(v, value)
	if isinstance(data, list):
		for x in data:
			if any([x for x in x.values() if isinstance(x, bool)]): yield x
			else: 
				yield from find_val(x, value)

def addToClipBoard(text):
    command = 'echo ' + text.strip() + '| clip'
    os.system(command)

####################################
	




####################################
###			PAGINATE RESULTS	 ###
####################################
def page_results(items):
	""" This method computers page ranges and page options from the search results and the current page displayed in the browers
	###PARAMETERS
	total : int
		- The total number of hits returned from the ES search query
	page : int
		- The page currently displayed on the browser
	"""
	pages = { 'num_pages' : (items['result']['total'] // RESULTS_SIZE) + (items['result']['total'] % RESULTS_SIZE > 0) }	# CALCULATE NUMBER OF PAGES REQUIRED
	if pages['num_pages'] > 0: pages['range'] = __create_page_ranges(items['result']['pages']['page'], pages['num_pages'])	# COMPUTE PAGES REQUIRED
	if items['result']['pages']['page'] > 1: pages['previous'] = items['result']['pages']['page'] - 1						# CHECK IF TEMPLATE NEEDS TO SHOW 'NEXT'
	if items['result']['pages']['page'] < pages['num_pages']: pages['next'] = items['result']['pages']['page'] + 1			# CHECK IF TEMPLATE NEEDS TO SHOW 'PREVIOUS'
	return pages

def __create_page_ranges(page, num_pages):
	""" This private method computes page ranges """
	# create the range of page numbers and ellipses to show
	# always show 1. attempt to show two page numbers around the current page
	num_pages_range = [1]

	# check if we need an ellipsis after 1
	if page - 2 > 2:
		num_pages_range.append(-1)

	# determine values before
	if page - 2 <= 1:
		for i in range(2, page+1):
			num_pages_range.append(i)
	else:
		for i in range(page-2, page):
			num_pages_range.append(i)

	# add current page if it's not first or last
	if page != 1 and page != num_pages and page not in num_pages_range:
		num_pages_range.append(page)

	# determine values after
	if page + 2 >= num_pages:
		for i in range(page+1, num_pages):
			num_pages_range.append(i)
	else:
		for i in range(page+1, page+3):
			num_pages_range.append(i)

	# check if we need an ellipsis before last page
	if page + 2 < num_pages - 1:
		num_pages_range.append(-1)

	# always append last page, check it's not already in there (when there are only a few pages)
	if num_pages not in num_pages_range:
		num_pages_range.append(num_pages)

	return num_pages_range
####################################
	




####################################
###		CHECK DATE PATTERNS		 ###
####################################
# THIS METHOD CHECKS A LIST OF STRINGS FOR AMERICAN AND EUROPEAN DATE PATTERNS, REMOVES THE VALUES FROM THE LIST AND CONVERTS THEM TO MILLISECONDS
# INPUTS: A LIST OF STRING VALUES
# OUTPUTS: TUPLE WITH REMAINDER OF THE LIST WITHOUT PROPER DATE VALUES AND LIST WITH CONVERTED DATE VALUES
def chkDatePattern(values):
	dates = {}
	for idx, value in enumerate(values):
		
		try:
			# CONVERT TO MONTH NUMBER IF VALUE IS A MONTH
			if value.lower() in MONTHS:

				addedDates = []
				pos = 0
				
				def recurseArray(dateRange, pos):

					if pos == len(dateRange):
						pos -= 1
					
					if len(dateRange) == 0:
						return addedDates

					# CHECK NEXT VALUE
					if dateRange[pos] is not '' and any(char.isdigit() for char in dateRange[pos]) and len(dateRange[pos]) <= 2 and int(dateRange[pos]) <= 31:
						addedDates.append(dateRange[pos])
						dateRange.pop(pos)
						return recurseArray(dateRange, pos)
					else:
						dateRange.pop(pos)
						return recurseArray(dateRange, pos)
				
				# CHECK IF ADJACENT VALUES FORM A COHERENT DATE
				dateRange = values[idx-3:idx+3]
				pos = dateRange.index(value) # POSITION OF VALUE TO BE CHECKED
				dateRange = [re.sub("[^-/0-9]", "", x) for x in dateRange] # CLEAN ARRAY VALUES
				year = "".join([x for x in dateRange if all(char.isdigit() for char in x) and len(x) == 4])
				
				if year:
					dateRange.pop(dateRange.index(year))                    
				else:
					# ASSUME YEAR BASED ON MOST COMMMON OCCURENCE IN CURRENT CONSTRUCTED DATES
					year = "".join(max(set([k.split('/')[2] for k in dates.keys()]), key=[k.split('/')[2] for k in dates.keys()].count))
				
				month = MONTHS.index(value.lower())+1

				day = ""
				
				dayOptions = recurseArray(dateRange, pos)

				if len(dayOptions) == 0:
					day = "01" # DEFAULT VALUE TO MAKE SEARCH WORK AND PROVIDE WIDEST RANGE
				elif len(dayOptions) == 1:
					day = "".join(dayOptions)
				else:
					print('multiple day options possible--have not yet come across a case like this, but have not extensively checked')
					# if ()
					# # WHICH OF THE DAY OPTIONS IS MOST REASONABLE?
					# for dayOption in dayOptions:
					#     distances = {}
					#     string, ms = convertToMS(f'{dayOption}{month}{year}')
					#     for date_ms in dates.values():
					#         distances[string] = abs(ms - date_ms)

					#     # GET LOWEST DISTANCE DIFFERENCE FROM DICT
					#     lowest = min(distances, key=distances.get)


				value = f'{month}/{day}/{year}'

				string, ms = convertToMS(value)

				if string not in dates and ms < -870091200:
					dates[string] = ms

			value = re.sub("[^-/0-9]", "", value)  # STRIP THE STRING OF ORDINALS

			if any(char.isdigit() for char in value):
				if len(value) <= 10:
					values[idx] = value
					if '-' in value or '/' in value:
						splitVal = value.split('-') if '-' in value else (value.split('/') if '/' in value else [0,0,0])
						if len(splitVal) == 3 and len(splitVal[2]) is 4 and int(splitVal[2]) > 1900 < 2000 and (
						(int(splitVal[0]) <= 12 and int(splitVal[1]) <= 31) or 
						(int(splitVal[0]) <= 31 and int(splitVal[1]) <= 12) or
						(int(splitVal[1]) <= 12 and int(splitVal[2]) <= 31) or
						(int(splitVal[1]) <= 31 and int(splitVal[2]) <= 12)) and (
							(int(splitVal[0]) < 2000 > 1890) or
							(int(splitVal[1]) < 2000 > 1890) or
							(int(splitVal[2]) < 2000 > 1890)
						):
							if '-' in value:
								value = value.split('-')
								val = copy.deepcopy(value)
								value[0] = val[1]
								value[1] = val[0]
								value = '/'.join(value)
							
							string, ms = convertToMS(value)
							if ms < -870091200:
								dates[string] = ms
					
					# WE ASSUME VALUE IS A YEAR 'YYYY'
					elif len(value) <= 4:
						# DEFINE RANGE AS BEGINNING OF YEAR AND END OF YEAR
						start = f'01/01/{value}'
						end = f'12/31/{value}'
						startStr, startMS = convertToMS(start)
						endStr, endMS = convertToMS(end)
						if startMS < -870091200: dates[startStr] = startMS
						if endMS < -870091200: dates[endStr] = endMS
		except:
			print(f'There was an error with {idx} in "values"')
	return dates

# THIS METHOD INTERPRETS A VERBAL DESCRIPTION OF A DATE PATTERN, MATCHING MONTH NAMES AGAINST A GLOBAL LIST
# INPUTS: A STRING
# OUTPUTS: TUPLE WITH BOOLEAN FOR SUCCESS AND LIST OF DICTS WITH DATES (KEYS) AND MILLISECONDS (VALUES) SORTED FROM EARLY TO LATE
def chkDate(value):
    try:
        value = str(value) # CHECK IF THE INPUT IS A STRING
        value = value.split(' ') # SPLIT ON SPACE

        # ITERATE OVER VALUES IN STRING LIST
        if len(value) > 0:
            dates = chkDatePattern(value)

        sorted_dates = sorted(dates.items(), key=operator.itemgetter(1))
        return (True, sorted_dates)
    except:
        return (False, "There was an error parsing the date string")

def convertToMS(value):
	splitVal = value.split('/')
	splitVal = [f'0{x}' if len(x) < 2 and int(x) <= 9 else x for x in splitVal]
	
	if len(splitVal) == 3 and len(splitVal[0]) <= 2 and len(splitVal[1]) <= 2 and len(splitVal[2]) <= 4:
		return "/".join(splitVal), (parser().parse(value)-datetime(1970,1,1)).total_seconds()
	elif len(splitVal[0]) == 4:
		return value, (parser().parse(value)-datetime(1970,1,1)).total_seconds()