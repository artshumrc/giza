from django import forms
from django.core import serializers
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse, resolve
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from utils.elastic_backend import es, ES_INDEX
from utils.views_utils import CATEGORIES, FACETS_PER_CATEGORY, FIELDS_PER_CATEGORY

from .forms import CustomUserCreationForm, CollectionForm
from .models import Collection, Lesson, ElasticsearchItem

RESULTS_SIZE = 20

def build_es_query(search_term, fields):
     if fields:
          must = []
          for k,v in list(fields.items()):
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

def build_subfacet_aggs(current_category, current_subfacets, bool_filter):
    if not current_category:
        return {}
    if current_category not in current_subfacets:
        return { name : term_agg for name, term_agg in list(FACETS_PER_CATEGORY[current_category].items()) }

    aggregations = {}
    aggs_for_selected = {}
    aggs_for_unselected = {}
    should = []
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

def user_login(request):
    # perform login
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                redirect_to = request.GET.get('redirect_to', None)
                next = request.GET.get('next', None)

                # no idea why the failed get is being cast to a string
                if redirect_to is not None and redirect_to != 'None':
                    return HttpResponseRedirect(redirect_to)
                elif next is not None and next != 'None':
                    return HttpResponseRedirect(next)
                return HttpResponseRedirect(reverse('index'))
            else:
                return HttpResponse("Your account is inactivate.")
        else:
            messages.error(request, "Wrong username or password.")
            return HttpResponseRedirect(reverse('login'))

    # show login form
    else:
        # render
        return render(request, 'pages/login.html', { 'redirect_to': request.GET.get('redirect_to') })

def sign_up(request):
    registered = False

    # perform registration
    if request.method == 'POST':
        custom_user = None
        custom_user_form = CustomUserCreationForm(data=request.POST)

        # save user
        if custom_user_form.is_valid():
            # create user
            custom_user = custom_user_form.save()
            public_group = Group.objects.get(name='Public')
            custom_user.groups.add(public_group)
            custom_user.save()
            registered = True
            return redirect('/')

        else:
            messages.error(request, "You were unable to create a new user account.")


    # show reg form
    else:
        custom_user_form = CustomUserCreationForm()

    # render
    context = {
        'custom_user_form': custom_user_form,
        'registered': registered
    }
    return render(request, 'pages/sign_up.html', context)

@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))

def mygiza(request):
    return render(request, 'pages/mygiza-landing.html')

def collections(request):
    collections = Collection.objects.all()

    return render(request, 'pages/mygiza-allcollections.html', {
        'collections': collections,
    })

def collections_user(request):
    collections = []
    if request.user:
        collections = Collection.objects.filter(owners=request.user.id)

    return render(request, 'pages/mygiza-allcollections.html', {
        'collections': collections,
    })

def collection(request, slug):
    collection = get_object_or_404(Collection, slug=slug)
    items = []
    hits = []

    search_term = request.GET.get('q', '')
    query = {}

    if collection.items.all():
        query = {
            'bool': {
                "should": [],
            }
        }
        for elasticsearch_item in collection.items.all():
            query['bool']['should'].append({
                'bool': {
                    'must': [
                        {
                            'term': {
                                "_type": elasticsearch_item.type,
                            }
                        },
                        {
                            'term': {
                                "_id": elasticsearch_item.es_id,
                            }
                        },
                    ]
                }
            })
    else:
        # pass a query that will get no values returned
        query = {
            'ids': {
                'type': '_doc',
                'values': []
            }
        }

    categorystring = ""
    current_category = request.GET.get('category', '')
    current_subfacets = {}
    bool_filter = {
        "must" : [],
    }
    sort = request.GET.get('sort', '_score')
    page = int(request.GET.get('page', 1))
    results_from = 0
    # calculate elasticsearch's from, using the page value
    results_from = (page - 1) * RESULTS_SIZE
    all_categories = {}
    sub_facets = {}
    has_next = False
    has_previous = False
    previous_page_number = 0
    next_page_number = 0
    num_pages_range = []
    num_pages = 0
    total = 0

    body_query = {
        "from": results_from,
        "size": RESULTS_SIZE,
        "query": query,
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
        "sort" : sort
    }

    subfacet_aggs = build_subfacet_aggs(current_category, current_subfacets, bool_filter)
    facets_for_category = es.search(index=ES_INDEX, body=body_query)

    facet_names = []
    if current_subfacets:
        for facet_name in list(current_subfacets[current_category].keys()):
            facet_names.append(facet_name)
    rec = recurse_aggs('', facets_for_category, [], facet_names)
    sub_facets[current_category] = rec

    search_results = es.search(index=ES_INDEX, body={
        "from": results_from,
        "size": RESULTS_SIZE,
        "query": query,
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
    if current_category and current_category in current_subfacets:
        for facet_name, facet_values in list(current_subfacets[current_category].items()):
            for value in facet_values:
                subfacet_strings.append("%s_%s_%s" % (current_category, facet_name, value))

    search_params = []
    if search_term:
        search_params.append(('q', 'Keyword', search_term))
    if current_category:
        for k, v in list(fields.items()):
            if v:
                search_params.append((current_category+'_'+k, FIELDS_PER_CATEGORY[current_category][k], v))

    return render(request, 'pages/mygiza-collection.html', {
        'collection': collection,
        'search_params' : search_params,
        'hits' : hits,
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
    })

def collections_create(request):

    # create a collection
    if request.method == 'POST':
        collection_form = CollectionForm(data=request.POST)

        # save user
        if collection_form.is_valid():
            # create user
            collection = collection_form.save()
            collection.owners.add(request.user)
            collection.save()

            return redirect('/collections/{}'.format(collection.slug))

        else:
            messages.error(request, "Error creating collection.")

    # show collection form
    else:
        collection_form = CollectionForm()

    return render(request, 'pages/mygiza-collection-edit.html', {
        'collection_form': collection_form,
    })

def collections_edit(request, slug):

    # create a collection
    if request.method == 'POST':
        collection_form = CollectionForm(data=request.POST)

        # save user
        if collection_form.is_valid():
            # create user
            collection = collection_form.save()
            collection.save()

            return redirect('/collections/{}'.format(collection.slug))

        else:
            messages.error(request, "Error creating collection.")

    # show collection form
    else:
        collection = get_object_or_404(Collection, slug=slug)
        collection_form = CollectionForm(collection)

        # user does not own this collection, redirect to collections page
        if not request.user in collection.owners.all():
            return redirect('/collections/')

        # handle adding new item id and type to collection
        if request.GET.get('add_item_id') and request.GET.get('add_item_type'):
            elasticsearch_item = ElasticsearchItem(
                    es_id=request.GET.get('add_item_id'),
                    type=request.GET.get('add_item_type'),
                    collection=collection
                )
            elasticsearch_item.save()
            return redirect('/collections/{}'.format(collection.slug))

        elif request.GET.get('remove_item_id') and request.GET.get('remove_item_type'):
            elasticsearch_item = ElasticsearchItem.objects.filter(
                    es_id=request.GET.get('remove_item_id'),
                    type=request.GET.get('remove_item_type'),
                    collection=collection
                )
            elasticsearch_item.delete()
            return redirect('/collections/{}'.format(collection.slug))

    return render(request, 'pages/mygiza-collection-edit.html', {
        'collection_form': collection_form,
    })

def lessons(request):
    lessons = Lesson.objects.all()

    return render(request, 'pages/lessons.html', {
        'lessons': lessons,
    })

def lesson(request, slug):
    lesson = get_object_or_404(Lesson, slug=slug)
    lessons = Lesson.objects.all()

    return render(request, 'pages/lesson.html', {
        'lesson': lesson,
        'lessons': lessons,
    })
