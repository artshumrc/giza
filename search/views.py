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
    search_query = request.GET.get('q', None)
    category = request.GET.getlist('category', [])
    category = list(map(lambda x: x.encode('utf-8'), category))
    categorystring = ",".join(category)
    page = int(request.GET.get('page', 1))
    results_from = 0
    # calculate elasticsearch's from, using the page value
    results_from = (page - 1) * RESULTS_SIZE
    print search_query, category, page, results_from

    # check if user is trying to search by specific item number
    number_query = False
    number = None
    parts = search_query.split(':')
    if len(parts) == 2:
        categorystring = parts[0]
        number = parts[1]
        number_query = True

    # values being passed to template
    hits = []
    category_facets = {}
    sub_facets = {}
    has_next = False
    has_previous = False
    previous_page_number = 0
    next_page_number = 0
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
        # this is a normal search, just aggregate by type/category
        ## Aggregations per type/category if we have categories

        for c in category:
            aggregations = {}
            for facet, field in FACETS_PER_CATEGORY[c].items():
                aggregations[facet] = {
                    "terms" : {
                        "field" : field
                    }
                }
            body_query = {
                "size" : 0,
                "query": {
                    "match_phrase": {
                       "_all": search_query
                    }
                },
                "aggregations": aggregations
            }
            facets_for_category = es.search(index=ES_INDEX, doc_type=c, body=body_query)
            sub_facets[c] = []
            if 'aggregations' in facets_for_category:
                for agg_name, value in facets_for_category['aggregations'].items():
                    facet_array = []
                    for bucket in value['buckets']:
                        agg = {
                        'display_text' : bucket['key'],
                        'doc_count' : bucket['doc_count']
                        }
                        facet_array.append(agg)
                    sub_facets[c].append({agg_name : facet_array})

        # get facets separately (not sure if these two searches can be combined)
        aggregations = es.search(index=ES_INDEX, body={
            "size" : 0,
            "query": {
                "match_phrase": {
                   "_all": search_query
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

        search_results = es.search(index=ES_INDEX, doc_type=categorystring, body={
            "from": results_from,
            "size": RESULTS_SIZE,
            "query": {
                "match_phrase": {
                   "_all": search_query
                }
            }
        })
        category_facets['types'] = []
        for count in aggregations['aggregations']['aggregation']['buckets']:
            category_facets['types'].append({
                'key' : count['key'],
                'doc_count' : count['doc_count'],
                'display_text' : CATEGORIES[count['key']]
                })
        print category_facets
        for hit in search_results['hits']['hits']:
            hits.append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})

        total = search_results['hits']['total']

        if page > 1:
            has_previous = True
            previous_page_number = page - 1
        if (total / RESULTS_SIZE > page) or (total / RESULTS_SIZE == page and total % RESULTS_SIZE > 0):
            has_next = True
            next_page_number = page + 1

    return render(request, 'search/results.html', {
        'search_query' : search_query,
        'hits' : hits,
        'category_facets' : category_facets,
        'sub_facets' : sub_facets,
        'total' : total,
        'has_previous' : has_previous,
        'previous_page_number' : previous_page_number,
        'has_next' : has_next,
        'next_page_number' : next_page_number,
        'categories' : category
    })
