from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from wagtail.wagtailcore.models import Page
from wagtail.wagtailsearch.models import Query
from utils.elastic_backend import es, ES_INDEX
from utils.views_utils import CATEGORIES, FACETS_PER_CATEGORY, FIELDS_PER_CATEGORY

RESULTS_SIZE = 20

def search(request):
    return render(request, 'search/search.html')

# get all pubdocs with pdfs for Digital Giza Library
def library(request):
    sort = request.GET.get('sort', 'name').encode('utf-8')
    if sort == 'name':
        results = es.search(index=ES_INDEX, doc_type='library', body={
            "size": 500,
            "sort": sort,
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
            if source['name'].encode('utf-8').lower().startswith(current_letter):
                letter_docs[current_letter].append(source)
            else:
                hits.append(letter_docs)
                current_letter = source['name'].encode('utf-8').lower()[0]
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
                    "field": sort+".raw",
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
    return render(request, 'search/library.html', {
        'results' : hits,
        'sort' : sort
    })

def results(request):
    search_term = request.GET.get('q', '').encode('utf-8')
    sort = request.GET.get('sort', '_score').encode('utf-8')
    current_category = request.GET.get('category', '').encode('utf-8')
    current_subfacets = {}
    fields = {}
    if current_category:
        # check if there are subfacets for the currently selected category
        subcats = request.GET.getlist(current_category+'_facet', [])
        if subcats: current_subfacets[current_category] = {}
        for sc in subcats:
            parts = sc.split('_')
            subfacet = parts[0]
            term = parts[1]
            if subfacet not in current_subfacets[current_category]:
                current_subfacets[current_category][subfacet] = []
            current_subfacets[current_category][subfacet].append(term)

        # check if we have a field-specific search
        for key in request.GET:
            if key.startswith(current_category) and not key.endswith('_facet'):
                field_value = request.GET.get(key, '').encode('utf-8')
                parts = key.split('_')
                field = parts[1]
                fields[field] = field_value

    page = int(request.GET.get('page', 1))
    results_from = 0
    # calculate elasticsearch's from, using the page value
    results_from = (page - 1) * RESULTS_SIZE

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
        base_query = build_es_query(search_term, current_category, current_subfacets, fields)
        bool_filter = build_bool(current_category, current_subfacets, '')
        subfacet_aggs = build_subfacet_aggs(current_category, current_subfacets, bool_filter)

        body_query = {
            "size" : 0,
            "query" : base_query,
            "aggregations" : subfacet_aggs,
            "post_filter" : {
                "bool" : bool_filter
            },
            "sort" : sort
        }
        facets_for_category = es.search(index=ES_INDEX, body=body_query)

        rec = recurse_aggs('', facets_for_category, [])
        sub_facets[current_category] = rec

        search_results = es.search(index=ES_INDEX, body={
            "from": results_from,
            "size": RESULTS_SIZE,
            "query": base_query,
            "aggregations": {
                "aggregation": {
                    "terms": {
                        "field": "_type"
                    }
                }
            },
            "post_filter" : {
                "bool" : bool_filter
            },
            "sort" : sort
        })
        all_categories['types'] = []
        for count in search_results['aggregations']['aggregation']['buckets']:
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
    if current_category and current_category in current_subfacets:
        for facet_name, facet_values in current_subfacets[current_category].items():
            for value in facet_values:
                subfacet_strings.append("%s_%s_%s" % (current_category, facet_name, value))

    search_params = []
    if search_term:
        search_params.append(('q', 'Keyword', search_term))
    if current_category:
        for k, v in fields.items():
            if v:
                search_params.append((current_category+'_'+k, FIELDS_PER_CATEGORY[current_category][k], v))

    return render(request, 'search/results.html', {
        'search_params' : search_params,
        'hits' : hits,
        'all_categories' : all_categories,
        'CATEGORIES' : CATEGORIES,
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
        'current_category' : current_category
    })

def recurse_aggs(agg_name, facets, sub_facets):
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
            sub_facets.append({agg_name : facet_array})
            return sub_facets
        else:
            for agg_name, value in facets.items():
                recurse_aggs(agg_name, value, sub_facets)
            return sub_facets
    else:
        for agg_name, value in facets['aggregations'].items():
            recurse_aggs(agg_name, value, sub_facets)
        return sub_facets

def build_subfacet_aggs(current_category, current_subfacets, bool_filter):
    if not current_category:
        return {}
    if current_category not in current_subfacets:
        return { name : term_agg for name, term_agg in FACETS_PER_CATEGORY[current_category].items() }

    aggregations = {}
    aggs_for_selected = {}
    aggs_for_unselected = {}
    should = []
    # aggregations for a facet that has been selected by the user will only be affected by other selected facets
    for name, term_agg in FACETS_PER_CATEGORY[current_category].items():
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

    filter_name = "_".join(current_subfacets[current_category].keys()) + "_filter"

    aggregations[filter_name] = {
        "filter" : {
            "bool" : bool_filter
        },
        "aggregations": aggs_for_unselected
    }

    return aggregations

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
            for facet_name, facet_values in current_subfacets[current_category].items():
                if facet_name == facet_name_ignore:
                    continue
                should = []
                for value in facet_values:
                    field_name = list(find_key('field', FACETS_PER_CATEGORY[current_category][facet_name]))[0]
                    should.append({"term": {field_name : value}})
                must.append({"bool" : {
                    "should" : should
                }})

    # set the 'filter'
    bool_filter = {
        "must" : must
    }
    return bool_filter

def build_es_query(search_term, current_category, current_subfacets, fields):
    if fields:
        must = []
        for k,v in fields.items():
            if v:
                must.append({
                    "match" : {
                        k : {
                            "query" : v,
                            "operator" : "and"
                        }
                    }
                })
        q = {
            "bool" : {
                "must" : must
            }
        }
    elif search_term == '':
        q = {
            "match_all" : {}
        }
    else:
        q = {
            "bool" : {
             "should" : [
                {
                   "match" : {
                      "displaytext" : {
                         "query" : search_term,
                         "operator" : "and",
                         "boost" : 2
                      }
                   }
                },
                {
                    "match" : {
                       "_all" : {
                        "query" : search_term,
                        "operator" : "and"
                       }
                    }
                }
             ]
          }
        }
    return q

def find_key(key, value):
    for k, v in value.iteritems():
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
