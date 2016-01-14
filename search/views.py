from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from wagtail.wagtailcore.models import Page
from wagtail.wagtailsearch.models import Query
from utils.elastic_backend import es, ES_INDEX
from utils.views_utils import RELATED_DISPLAY_TEXT

def search(request):
    search_query = request.GET.get('q', None)
    type = request.GET.get('type', None)
    # check if user is trying to search by specific item number
    number_query = False
    number = None
    parts = search_query.split(':')
    if len(parts) == 2:
        type = parts[0]
        number = parts[1]
        number_query = True

    hits = []
    counts = {}
    if number_query:
        # user is searching for an exact item using its number
        # such as 'finds:HUMFA_27-5-1'
        search_results = es.search(index=ES_INDEX, doc_type=type, body={
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
            return HttpResponseRedirect(reverse(type, args=(source.get('id'),)))
        elif results_total == 0 and type == 'sites':
            
        else:
            # we have 0 or more than 1 result, treat it as a normal search result
            # this shouldn't happen, since we are doing a termed search on number
            # it expects an exact match
            for hit in search_results['hits']['hits']:
                hits.append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})
    elif type:
        # searching a phrase with a specific type
        # error check type
        search_results = es.search(index=ES_INDEX, doc_type=type, body={
            "query": {
                "match_phrase": {
                   "_all": search_query
                }
            }
        })
        print search_results['hits']['total']
        for hit in search_results['hits']['hits']:
            hits.append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})
    else:
        # this is a normal search, just aggregate by type
        search_results = es.search(index=ES_INDEX, search_type='count', body={
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
        for count in search_results['aggregations']['aggregation']['buckets']:
            counts[count['key']] = {
                'doc_count' : count['doc_count'],
                'display_text' : RELATED_DISPLAY_TEXT[count['key']]
                }
    
    return render(request, 'search/search.html', {
        'search_query' : search_query,
        'hits' : hits,
        'counts' : counts,
    })

