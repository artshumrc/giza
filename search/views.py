from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from wagtail.wagtailcore.models import Page
from wagtail.wagtailsearch.models import Query
from utils.elastic_backend import es, ES_INDEX


def search(request):
    search_query = request.GET.get('q', None)
    type = request.GET.get('type', None)
    q = '_all:%s' % search_query
    hits = []
    counts = []
    if type:
        # error check type
        search_results = es.search(index=ES_INDEX, q=q, doc_type=type)
        for hit in search_results['hits']['hits']:
            hits.append({'id' : hit.get('_id'), 'type' : hit.get('_type'), 'source' : hit.get('_source')})
    else:
        # just get result counts for each type
        search_results = es.search(index=ES_INDEX, search_type='count', body={
            "query": {
                "query_string": {
                   "query": search_query
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
            counts.append(count)
    print hits
    
    return render(request, 'search/search.html', {
        'search_query' : search_query,
        'hits' : hits,
        'counts' : counts,
    })
    # Search
    # if search_query:
    #     search_results = Page.objects.live().search(search_query)
    #     query = Query.get(search_query)

    #     # Record hit
    #     query.add_hit()
    # else:
    #     search_results = Page.objects.none()

    # # Pagination
    # paginator = Paginator(search_results, 10)
    # try:
    #     search_results = paginator.page(page)
    # except PageNotAnInteger:
    #     search_results = paginator.page(1)
    # except EmptyPage:
    #     search_results = paginator.page(paginator.num_pages)

    # return render(request, 'search/search.html', {
    #     'search_query': search_query,
    #     'search_results': search_results,
    # })
