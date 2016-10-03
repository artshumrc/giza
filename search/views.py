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
        'num_pages_range' : num_pages_range,
        'num_pages' : num_pages,
        'current_page' : str(page),
        'categories' : category
    })

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
