from typing import ValuesView
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
import copy, re, operator, json, inspect
import numpy as np

from dateutil.parser import parse
from dateutil.parser import parser
from datetime import *

from utils.elastic_backend import es, ES_INDEX
from utils.views_utils import CATEGORIES, FACETS_PER_CATEGORY, FIELDS_PER_CATEGORY

RESULTS_SIZE = 20

REGEXP = '[-@_!#$%^&*()<>?/\|}{~:,]'

MONTHS = [
    'january',
    'february',
    'march',
    'april',
    'may',
    'june',
    'july',
    'august',
    'september',
    'october',
    'november',
    'december'
]

def search(request):
	return render(request, 'pages/search.html')

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

# SEARCH FUNCTION
# This function processes the request by first extracting the search category/categories and then 
# INPUT: HEADER REQUEST OBJECT
def results(request):

	#########################
	#	BASE PARAMS			#
	#########################

	# COMPUTE INDEX FOR BEGINNING OF ES SEARCH RESULTS
	page = int(request.GET.get('page', 1))
	results_from = (page - 1) * RESULTS_SIZE
	
	# VALUES PASSED TO TEMPLATE AT THE END
	all_categories, sub_facets, total = {}, {}, 0	# CATEGORIES, FACETS AND TOTAL NUMBER OF HITS
	has_next, has_previous = False, False			# IF SEARCH RESULTS IN PREV OR NEXT PAGES (DEFAULT FALSE)
	previous_page_number, next_page_number = 0, 0	# NUMBER OF PREV OR NEXT PAGES
	num_pages, num_pages_range = 0, []				# NUMEBR OF PAGES TOTAL, RANGE OF PAGES
	category, all_categories['types'], search_params, search_terms, fields, subfacet_strings = "", [], [], {}, {}, []

	current_subfacets, fields, hits, results_from, search_results = {}, {}, [], 0, None

	# COPY REQUEST PARAMETERS IN DICTIONARY
	items = { k.replace('amp;', '') : v for k, v in request.GET.items()}
	facetList = { k.replace('amp;', '') : v for k, v in request.GET.lists() for k in items.keys() if 'facet' in k }
	items.update({ k : v for k, v in facetList.items() if 'facet' in k })

	#########################
	#	SIMPLE SEARCH		#
	#########################

	# GET SEARCH TERMS FROM SIMPLE SEARCH BOX (SINGLE STRING)
	search_term = request.GET.get('q', '')

	# USER DID NOT PROVIDE A SEARCH QUERY
	if search_term == '' and 'category' not in items and len(items) == 0:
		search_results = es.search(index=ES_INDEX, body={"query" : { "match_all" : { } } })
	
	# USER PROVIDED A SEARCH QUERY WITH COLON AND MAY BE LOOKING FOR A SPECIFIC OBJECT (E.G.: 'objects:HUMFA_27-5-1')
	elif ':' in search_term:
		parts = search_term.split(':')
		if len(parts) > 1 and parts[0] in CATEGORIES:
			search_results = es.search(index=ES_INDEX, doc_type=parts[0], body={"query" : { "match" : { "allnumbers" : { parts[1] } } } })
			
			# ONE RESULT WILL IMMEDIATELY DIRECT TO RESULT PAGE
			if search_results['hits']['total'] == 1:
				return HttpResponseRedirect(reverse('get_type_html', args=(parts[0], search_results['hits']['hits'][0].get('_source').get('id'), 'full')))
			else:
				print(f'Unique number search at {inspect.getframeinfo(inspect.currentframe()).lineno} resulted in more than one record')
				# STOP-MEASURE: RETURN ALL OR NO RESULTS
				for hit in search_results['hits']['hits']:
					hits.append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})

	#########################
	#	ADVANCED SEARCH		#
	#########################

	# USER DID AN ADVANCED SEARCH
	else:

		# GET CATEGORY IF ADVANCED SEARCH
		category = items['category'] if 'category' in items else ""
		category = list({ k.split('_')[0] for k in items.keys() if k.split('_')[0] is not 'q' }) if category == "" else category
		category = category[0] if type(category) is not str and len(category) > 0 else category
		# category = "" if len(category) == 0 else category
		# SEARCH CATEGORY IS SPECIFIED
		if category:
			
			# EXTRACT ALL RELATED SEARCH FIELD DATA
			fields = { k.split('_', -1)[1] : v for k, v in items.items() if k.startswith(category) and not k.endswith('_facet')}
			print(fields)

			# CHECK IF USER IS SEARCHING FOR DATE OR DATE RANGE
			newFields = copy.deepcopy(fields)
			for (key, value) in fields.items():
				if 'date' in key and value is not '': 
					res = chkDate(value)
					if res[0]:
						newFields[f'{key}_ms'] = {}
						newFields[f'{key}_ms'] = [str(x[1]) for x in res[1]]
			fields = newFields

			# EXTRACT ALL SEARCH TERMS FROM PREVIOUS SEARCH (IF ANY) -- Q: WHERE AND WHEN TO USE THESE? IS LIKE FIELDS, BUT NEEDS CATEGORY APPENDED?
			search_terms['category'] = items['category'] if 'category' in items and items['category'] is not '' else category
			search_terms['fields'] = { k : v for k, v in fields.items() if v is not '' }
			search_terms['facets'] = { k.split('_')[1] : v for k, v in items.items() if '_facet' in k }
			
			# EXTRACT ALL RELATED SUBFACETS
			facets = {k : v for k, v in items.items() if '_facet' in k}
			
			# IF FACETS FOUND IN SEARCH QUERY
			if facets: 
				current_subfacets[category] = {}
				# facets = [facets] if isinstance(facets, str) else facets # CONVERT TO LIST IF ONLY ONE STRING IS PASSED IN

				# # PROCESS SUB-CATEGORIES
				for facetvalue in facets.values():
					for value in facetvalue:
						k, v = value.split('_')
						if k not in current_subfacets[category]:
							current_subfacets[category][k] = []
						current_subfacets[category][k].append(v)
	

		# POPULATE CATEGORY AND FIELDS IF NOT PRESENT IN QUERY YET
		# category = [k.split('_')[0] for k in items.keys() if l.split('_')[0] is not 'q'][0] if category == '' else category
		# fields = { k.split('_')[1] : v for k, v in items.items() } if len(fields) == 0 and len(items) != 0 else fields

	#########################
	#	PROCESS SEARCH Q	#
	#########################
	base_query = build_es_query(search_term, fields) 													# BUILD NORMAL BASE JSON QUERY
	bool_filter = build_bool(category if category else "", current_subfacets, '') 						# BUILD BOOLEAN FILTERS
	subfacet_aggs = build_subfacet_aggs(category if category else "", current_subfacets, bool_filter)	# AGGREGATE RELATED FACETS

	# THE QUERY SEND TO ELASTICSEARCH TO FIND ALL RELATED ITEMS
	facets_for_category = es.search(index=ES_INDEX, body=body_query(base_query, subfacet_aggs, bool_filter, request.GET.get('sort', '_score')))

	facet_names = []
	if current_subfacets:
		for facet_name in list(current_subfacets[category].keys()):
			facet_names.append(facet_name)
	rec = recurse_aggs('', facets_for_category, [], facet_names)
	sub_facets[category if 'category' in items else ""] = rec

	# THE QUERY SEND TO ELASTICSEARCH TO FIND ITEMS TO SHOW?
	search_results = es.search(index=ES_INDEX, body={
		"from": results_from,
		"size": RESULTS_SIZE,
		"query": base_query,
		"aggregations": {
			"aggregation": {
				"terms": {
					"field": "_type",
					"exclude": "library", # ignore special type, library, which is used for the Digital Giza Library page
					"size" : 50 # make sure to get all categories (rather than just 10)
				}
			}
		},
		"post_filter" : {
			"bool" : bool_filter
		},
		"sort" : request.GET.get('sort', '_score')
	})

	# ITERATING OVER AGGREGATED RESULTS TO CATEGORIZE THEM
	for count in search_results['aggregations']['aggregation']['buckets']:
		all_categories['types'].append({
			'key' : count['key'],
			'doc_count' : count['doc_count'],
			'display_text' : CATEGORIES[count['key']]
			})

	for hit in search_results['hits']['hits']:
		hits.append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})

	total = search_results['hits']['total']

	# CALCULATE NUMBER OF PAGES REQUIRED
	num_pages = (total // RESULTS_SIZE) + (total % RESULTS_SIZE > 0)
	if num_pages > 0:
		num_pages_range = create_page_ranges(page, num_pages)

	if page > 1:
		has_previous = True
		previous_page_number = page - 1
	if page < num_pages:
		has_next = True
		next_page_number = page + 1

	# combine the current_subfacets into strings for quick comparison in template
	subfacet_strings = []
	if category and category in current_subfacets:
		for facet_name, facet_values in list(current_subfacets[category].items()):
			for value in facet_values:
				subfacet_strings.append(f'{category}_{facet_name}_{value}')

	# PREPARE THE SEARCH TERMS TO SEND BACK TO THE USER FOR THE FACETS BOX
	search_params = []
	if search_term:
		search_params.append(('q', 'Keyword', search_term))
	if category:
		for k, v in list(fields.items()):
			if v and '_ms' not in k:
				search_params.append((category+'_'+k, FIELDS_PER_CATEGORY[category][k], v))

	return render(request, 'pages/searchresults.html', {
		'search_params' : search_params,
		'search_terms': search_terms,
		'fields' : fields,
		'hits' : hits,
		'all_categories' : all_categories,
		'CATEGORIES' : CATEGORIES,
		'sub_facets' : sub_facets, # ALL RELATED MATERIALS
		'current_subfacets' : current_subfacets,
		'subfacet_strings' : subfacet_strings,
		'total' : total,
		'has_previous' : has_previous,
		'previous_page_number' : previous_page_number,
		'has_next' : has_next,
		'next_page_number' : next_page_number,
		'num_pages_range' : num_pages_range,
		'num_pages' : num_pages,
		'current_category' : category,
		'current_page' : str(page)
	})

def build_query(operator, field, term):
	if "match_all" in operator:
		q = { operator : {}}
	else:
		q = { 
				operator: { 
					field : term 
					} 
				}
	return  q

def body_query(base_query, subfacet_aggs, bool_filter, sort):
	q = {
		"size" : 0,
		"query" : base_query,
		"aggregations" : subfacet_aggs,
		"post_filter" : {
			"bool" : bool_filter
		},
		"sort" : sort
	}
	return q

# THIS METHOD AGGREGATES ALL SEARCH RESULTS INTO THE CATEGORIES FOR VIEWING ON THE CLIENT SIDE
def recurse_aggs(agg_name, facets, sub_facets, facet_names):
	if type(facets) != type(dict()):
		return sub_facets

	if 'aggregations' not in facets:
		facet_array = []
		if 'buckets' in facets:
			for bucket in facets['buckets']:
				agg = {
				'display_text' : bucket['key'],
				'doc_count' : bucket['doc_count']
				}
				facet_array.append(agg)
			if agg_name in facet_names:
				sub_facets.insert(0, {agg_name : facet_array})
			else:
				sub_facets.append({agg_name : facet_array})
			return sub_facets
		else:
			for agg_name, value in list(facets.items()):
				recurse_aggs(agg_name, value, sub_facets, facet_names)
			return sub_facets
	else:
		for agg_name, value in list(facets['aggregations'].items()):
			recurse_aggs(agg_name, value, sub_facets, facet_names)
		return sub_facets

# THIS METHOD BUILDS THE SUBFACETS AND RETURNS ALL AGGREGATED SUBFACETS
def build_subfacet_aggs(current_category, current_subfacets, bool_filter):
	if not current_category:
		return {}
	if current_category not in current_subfacets:
		return { name : term_agg for name, term_agg in list(FACETS_PER_CATEGORY[current_category].items()) }

	aggregations = {}
	# aggs_for_selected = {}
	aggs_for_unselected = {}
	# should = []
	# aggregations for a facet that has been selected by the user will only be affected by other selected facets
	for name, term_agg in list(FACETS_PER_CATEGORY[current_category].items()):
		if name in current_subfacets[current_category]:
			bool_filter_for_facet = build_bool(current_category, current_subfacets, name)
			filter_name = name + "_selected_filter"
			aggregations[filter_name] = {
				"filter" : {
					"bool" : bool_filter_for_facet
				},
				"aggregations": {
					name : term_agg
				}
			}
		else:
			# other aggregations will be filtered by the selected facets
			aggs_for_unselected[name] = term_agg

	filter_name = "_".join(list(current_subfacets[current_category].keys())) + "_filter"

	aggregations[filter_name] = {
		"filter" : {
			"bool" : bool_filter
		},
		"aggregations": aggs_for_unselected
	}

	return aggregations

# THIS METHOD BUILDS A BOOL FILTER
def build_bool(current_category, current_subfacets, facet_name_ignore):
	# strucure should be at the top level a must bool
	# each facet type is a should bool with all selected values in the array
	# the should bool is an item in the must bool array
	# current_category is in item in the must bool array

	must = []
	if current_category:
		must.append({
			"type" : {
				"value" : current_category
			}
		})
		if current_category in current_subfacets:
			for facet_name, facet_values in list(current_subfacets[current_category].items()):
				if facet_name == facet_name_ignore:
					continue
				should = []
				for value in facet_values:
					field_name = list(find_key('field', FACETS_PER_CATEGORY[current_category][facet_name]))[0]
					if 'nested' in FACETS_PER_CATEGORY[current_category][facet_name]:
						path = FACETS_PER_CATEGORY[current_category][facet_name]['nested']['path']
						should.append({"nested":
							{"path": path,
							"query" : {"term": {field_name : value}}
							}})
					else:
						should.append({"term": {field_name : value}})
				must.append({"bool" : {
					"should" : should
				}})

	# set the 'filter'
	bool_filter = {
		"must" : must
	}
	return bool_filter

# THIS METHOD BUILDS THE ELASTIC SEARCH BASE QUERY
# INPUT: 
# 	- SEARCH_TERM: STRING
# 	- FIELDS: DICT WITH FIELDS FROM ADVANCED SEARCH
# OUTPUT: dict WITH QUERY
def build_es_query(search_term, fields):
	q, should, must = {}, [], []
	q['bool'] = {}

	# IF SEARCH_TERM IS PROVIDED, CONSTRUCT SHOULD-QUERY
	if search_term:
		should.append({ "match" : { "_all" : { "query" : search_term } } })
		q['bool'] = { "should" : should }

	# IF FIELDS ARE PROVIDED, CONSTRUCT A MUST-QUERY
	if fields:
		for k, v in list(fields.items()):

			# RANGE MATCH BY MS
			if v and 'date' in k and '_ms' in k:
				must.append({ "match" : { k : int(float(v[0])) } }) if len(v) == 1 else must.append({ "range" : { k : { "gte" : int(float(v[0])), "lte" : int(float(v[1])) } } })
			
			# APPEND ANYTHING ELSE
			if v and 'date' not in k:
				must.append({ "match" : { k : { "query" : v } } })
		q['bool'] = { "must" : must }

	# IF NO SEARCH TERM OR FIELDS ARE PROVIDED RETURN EVERYTHING IN DATABASE
	if search_term == '' and len(fields) == 0:
		q = { "match_all" : {}}

	return q

def find_key(key, value):
	for k, v in value.items():
		if k == key:
			yield v
		elif isinstance(v, dict):
			for result in find_key(key, v):
				yield result
		elif isinstance(v, list):
			for d in v:
				for result in find_key(key, d):
					yield result

def create_page_ranges(page, num_pages):
	# create the range of page numbers and ellipses to show
	# always show 1. attempt to show two page numbers around the current page
	num_pages_range = ["1"]

	# check if we need an ellipsis after 1
	if page - 2 > 2:
		num_pages_range.append('ellipsis')

	# determine values before
	if page - 2 <= 1:
		for i in range(2, page+1):
			num_pages_range.append(str(i))
	else:
		for i in range(page-2, page):
			num_pages_range.append(str(i))

	# add current page if it's not first or last
	if page != 1 and page != num_pages and str(page) not in num_pages_range:
		num_pages_range.append(str(page))

	# determine values after
	if page + 2 >= num_pages:
		for i in range(page+1, num_pages):
			num_pages_range.append(str(i))
	else:
		for i in range(page+1, page+3):
			num_pages_range.append(str(i))

	# check if we need an ellipsis before last page
	if page + 2 < num_pages - 1:
		num_pages_range.append('ellipsis')

	# always append last page, check it's not already in there (when there are only a few pages)
	if str(num_pages) not in num_pages_range:
		num_pages_range.append(str(num_pages))

	return num_pages_range

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


            if any(char.isdigit() for char in value) and len(value) <= 10:
                values[idx] = value
                splitVal = value.split('-') if '-' in value else (value.split('/') if '/' in value else [0,0,0])
                if '-' in value or '/' in value:
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
        t = (parser().parse(value)-datetime(1970,1,1)).total_seconds()
        return "/".join(splitVal), t