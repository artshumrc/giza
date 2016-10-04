from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from wagtail.wagtailcore.models import Page
from wagtail.wagtailsearch.models import Query
from utils.elastic_backend import es, ES_INDEX
from utils.views_utils import CATEGORIES, FACETS_PER_CATEGORY

RESULTS_SIZE = 20

def search(request):
    return render(request, 'search/search.html')

def results(request):
    search_term = request.GET.get('q', None).encode('utf-8')
    current_categories = request.GET.getlist('category', [])
    current_categories = list(map(lambda x: x.encode('utf-8'), current_categories))
    current_subfacets = {}
    # check if there are subfacets for each category
    for c in current_categories:
        subcats = request.GET.getlist(c+'_facet', [])
        if subcats: current_subfacets[c] = {}
        for sc in subcats:
            parts = sc.split('_')
            subfacet = parts[0]
            term = parts[1]
            current_subfacets[c][subfacet] = term

    page = int(request.GET.get('page', 1))
    results_from = 0
    # calculate elasticsearch's from, using the page value
    results_from = (page - 1) * RESULTS_SIZE
    #print search_term, current_categories, current_subfacets, page, results_from

    # check if user is trying to search by specific item number
    number_query = False
    number = None
    parts = search_term.split(':')
    categorystring = ""
    if len(parts) == 2:
        categorystring = parts[0]
        number = parts[1]
        number_query = True

    # values being passed to template
    hits = []
    all_categories = {}
    sub_facets = {}
    has_next = False
    has_previous = False
    previous_page_number = 0
    next_page_number = 0
    num_pages_range = []
    num_pages = 0
    total = 0

    if number_query:
        # user is searching for an exact item using its number
        # such as 'objects:HUMFA_27-5-1'
        search_results = es.search(index=ES_INDEX, doc_type=categorystring, body={
          "query": {
            "term": {
                "number": number
            }
          }
        })
        results_total = search_results['hits']['total']
        # user entered a number that only has one result for the given type, redirect to that page
        if results_total == 1:
            source = search_results['hits']['hits'][0].get('_source')
            return HttpResponseRedirect(reverse('get_type_html', args=(categorystring, source.get('id'), 'intro')))
        #elif results_total == 0 and type == 'sites':
        else:
            # we have 0 or more than 1 result, treat it as a normal search result
            # this shouldn't happen, since we are doing a termed search on number
            # it expects an exact match
            for hit in search_results['hits']['hits']:
                hits.append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})
    else:
        # this is a normal search
        base_query = build_es_query(search_term, current_categories, current_subfacets)

        ## create the aggregations query for ES
        aggregations = {}
        for c in current_categories:
            aggregations[c+'.aggs'] = {
                "filter" : {
                    "type" : {
                        "value" : c
                    }
                },
                "aggregations" : { facet:{"terms" : {"field": field}} for facet, field in FACETS_PER_CATEGORY[c].items() }
            }
        body_query = {
            "size" : 0,
            "query": base_query,
            "aggregations": aggregations
        }

        facets_for_category = es.search(index=ES_INDEX, body=body_query)

        # build out the subfacets for display in template
        if 'aggregations' in facets_for_category:
            for agg_type, results in facets_for_category['aggregations'].items():
                cat_name = agg_type.split('.')[0]
                sub_facets[cat_name] = []
                for agg_name, value in results.items():
                    facet_array = []
                    if type(value) == type(dict()) and 'buckets' in value:
                        for bucket in value['buckets']:
                            agg = {
                            'display_text' : bucket['key'],
                            'doc_count' : bucket['doc_count']
                            }
                            facet_array.append(agg)
                        sub_facets[cat_name].append({agg_name : facet_array})

        # get category facets (not sure if this can be combined with the phrase search)
        # this search does not care if certain types have already been selected (unlike subfacets)
        aggregations = es.search(index=ES_INDEX, body={
            "size" : 0,
            "query": {
                "match_phrase": {
                   "_all": search_term
                }
            },
            "aggregations": {
                "aggregation": {
                    "terms": {
                        "field": "_type"
                    }
                }
            }
        })

        search_results = es.search(index=ES_INDEX, body={
            "from": results_from,
            "size": RESULTS_SIZE,
            "query": base_query
        })
        all_categories['types'] = []
        for count in aggregations['aggregations']['aggregation']['buckets']:
            all_categories['types'].append({
                'key' : count['key'],
                'doc_count' : count['doc_count'],
                'display_text' : CATEGORIES[count['key']]
                })
        for hit in search_results['hits']['hits']:
            hits.append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})

        total = search_results['hits']['total']

        num_pages = (total/RESULTS_SIZE) + (total % RESULTS_SIZE > 0)
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
    for category, subfacets in current_subfacets.items():
        for k,v in subfacets.items():
            subfacet_strings.append("%s_%s_%s" % (category, k, v))

    return render(request, 'search/results.html', {
        'search_term' : search_term,
        'hits' : hits,
        'all_categories' : all_categories,
        'sub_facets' : sub_facets,
        'current_subfacets' : current_subfacets,
        'subfacet_strings' : subfacet_strings,
        'total' : total,
        'has_previous' : has_previous,
        'previous_page_number' : previous_page_number,
        'has_next' : has_next,
        'next_page_number' : next_page_number,
        'num_pages_range' : num_pages_range,
        'num_pages' : num_pages,
        'current_page' : str(page),
        'current_categories' : current_categories
    })

def build_es_query(search_term, current_categories, current_subfacets):
    if len(current_subfacets.keys()) == 0:
        filter = {
            "bool" : {
                "should" : list(map(lambda x: {"type" : {"value" : x}}, current_categories))
            }
        }
    else:
        # build out the 'must' bool query
        must = []
        for k,v in current_subfacets.items():
            must.append({"type" : {"value" : k}})
            for name, value in v.items():
                must.append({"term": {FACETS_PER_CATEGORY[k][name] : value}})

        # build out the 'should' bool query, that uses 'must'
        should = []
        should.append({
            "bool" : {
                "must" : must
            }
        })
        for c in current_categories:
            if c not in current_subfacets:
                should.append({"type" : {"value" : c}})

        # set the 'filter'
        filter = {
            "bool" : {
                "should" : should
            }
        }

    q = {
        "filtered": {
            "query": {
                "match_phrase": {
                   "_all": search_term
                }
            },
            "filter" : filter
        }
    }
    return q

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
