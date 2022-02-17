import copy, re, operator, json, os
from logging import exception
from json.decoder import JSONDecodeError

from django.contrib.sites.shortcuts import get_current_site
from django.http.response import Http404, JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import render
from django.core.handlers.wsgi import WSGIRequest
from django.contrib.auth.decorators import login_required

from giza.forms import CollectionForm
from tms import models
from tms import views as tmsViews

from functools import reduce

from dateutil.parser import parser
from datetime import *

from utils.elastic_backend import es, ES_INDEX
from utils.views_utils import (
    CATEGORIES,
    FIELDS_PER_CATEGORY,
    SEARCH_FIELDS_PER_CATEGORY,
    SORT_FIELDS_PER_CATEGORY,
    FACETS_PER_CATEGORY,
    MET_SIMPLE,
    MET_SIMPLE_REVERSED,
    MONTHS,
)

####################################
###				ROUTES			 ###
####################################
# def search(request):
# return render(request, 'pages/search.html')


def search_show(request):
    return render(request, "pages/searchresults.html")

def search_results(request, items=None):
    """This route passes the Django Request object on to the base parameters method and will receive the items dictionary.
    It then renders the initial search_results page with items and returns the HTML to the user.
    ###Parameters
    - request : Django request object
            - The request sent from the client to the server
    ###Returns
    - Render function with template
    """
    try:
        if items is None:
            return JsonResponse(
                {
                    "success": True,
                    "html": {
                        "#main_content": {
                            "html": render_to_string(
                                "search-results.html", compile_results(request)
                            )
                        }
                    },
                }
            )
        else:
            if items:
                return compile_results(items)
            else:
                return []
    except Exception as e:
        print(e)
        return error(request, 404)


def search_results_update(request, items=None):
    """This route reprocesses the new search parameters that are sent from the frontend.
    The method first calls search_execute, which is detailed below and will result in a new items global object, which
    forms the basis to recompile the various templates required on the frontend.
    ###Parameters
    -	request : Django Request Object
            - The Django Request object sent from the frontend
    """
    if items is None:
        return JsonResponse(compile_update(request))
    else:
        items["user"] = request.user.is_authenticated
        if request.method == "GET":
            return compile_results(items)
        else:
            return compile_update(items)
        # else:
        # return JsonResponse({'status':'false','message': "Server error"}, status=500)


def compile_results(items):
    """
    This method returns the search results for a vanilla render/page redirect.
    Key names do not map onto the template.
    """
    items = search_execute(request=items)
    return {
        "stats": items["search"],
        "search_result": items["search"]["result"],
        # 'search' : items['search'],
        "search_params": items["search"],
        "search_pagination": items["search"]["result"],
        "search_categories": items["search"],
        "search_MET": items["search"]["MET"]["MET_tree"],
        "search": items["search"],
        "search_options": items["search"],
        "user": items["user"] if not items["user"].is_anonymous else None,
    }


def compile_update(items):
    """
    This method returns the search results for returning in a JsonResponse.
    The keys correspond to the id's declared in the template 'search-results.html'
    """
    items = search_execute(request=items)
    return {
        "search_stats": render_to_string(
            "search-stats.html",
            {
                "search": items["search"],
            },
        ),
        "search_result": render_to_string(
            "search-result.html",
            {
                "search_result": items["search"]["result"],
                "user": items["user"],
            },
        ),
        "search_facets": render_to_string(
            "search-facets.html",
            {
                "search": items["search"],
            },
        ),
        "search_params": render_to_string(
            "search-params.html",
            {
                "search_params": items["search"],
            },
        ),
        "search_pagination": render_to_string(
            "search-pagination.html",
            {
                "search_result": items["search"]["result"],
            },
        ),
        "search_categories": render_to_string(
            "search-categories.html",
            {
                "search": items["search"],
            },
        ),
        "search_options": render_to_string(
            "search-options.html",
            {
                "search": items["search"],
            },
        ),
        "search_MET": render_to_string(
            "search-MET.html",
            {
                "MET_tree": items["search"]["MET"]["MET_tree"],
            },
        ),
        "search": items["search"],
    }


####################################
###				LIBRARY			 ###
####################################
# get all pubdocs with pdfs for Digital Giza Library
def library(request):
    sort = request.GET.get("sort", "name")
    if sort == "name":
        results = es.search(
            index=ES_INDEX,
            doc_type="library",
            body={
                "size": 500,
                "sort": "sort" + sort,
                "query": {
                    "match_all": {},
                },
            },
        )["hits"]["hits"]
        current_letter = "a"
        hits = []
        letter_docs = {}
        letter_docs[current_letter] = []
        for r in results:
            source = r["_source"]
            if source["name"].lower().startswith(current_letter):
                letter_docs[current_letter].append(source)
            else:
                hits.append(letter_docs)
                current_letter = source["name"].lower()[0]
                letter_docs = {}
                letter_docs[current_letter] = []
                letter_docs[current_letter].append(source)
        hits.append(letter_docs)
    else:
        # year, format - TODO: title
        results = es.search(
            index=ES_INDEX,
            doc_type="pubdocs",
            body={
                "size": 0,
                "query": {
                    "match_all": {},
                },
                "aggs": {
                    "by_sort": {
                        "terms": {
                            "field": sort + ".keyword",
                            "order": {
                                "_term": "asc",
                            },
                            "size": 500,
                        },
                        "aggs": {
                            "by_top_hit": {
                                "top_hits": {
                                    "size": 100,
                                },
                            },
                        },
                    }
                },
            },
        )["aggregations"]["by_sort"]["buckets"]
        hits = []
        for r in results:
            sort_docs = {}
            key = r["key"]
            sort_docs[key] = []
            docs = []
            sort_docs[key].append({"docs": docs})
            for h in r["by_top_hit"]["hits"]["hits"]:
                if "pdf" in h["_source"] and h["_source"]["pdf"] != "":
                    docs.append(
                        {
                            "url": h["_source"]["pdf"],
                            "displaytext": h["_source"]["boilertext"],
                            "format": h["_source"]["format"],
                        }
                    )
            if len(docs) > 0:
                hits.append(sort_docs)

    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string(
                        "pages/library.html",
                        {
                            "results": hits,
                            "sort": sort,
                        },
                    ),
                },
            },
        },
    )


####################################
###			TOUR VIDEOS			 ###
####################################
# get virtual Giza tour videos
def videos(request):
    results = es.search(
        index=ES_INDEX,
        doc_type="videos",
        body={
            "size": 500,
            "query": {
                "wildcard": {
                    "number": "gph_3dp*",
                },
            },
            "sort": "displaytext.keyword",
        },
    )["hits"]["hits"]
    hits = []

    for r in results:
        hits.append(r["_source"])

    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string(
                        "videos.html",
                        {
                            "results": hits,
                        },
                    ),
                },
            },
        },
    )


def get_type_html(request, type, id, view):
    # get site in elasticsearch and render or return 404
    # try:
    if view == "intro":
        view = "full"
    type_object = models.get_item(id, type, ES_INDEX)

    if "relateditems" in type_object:
        for item in type_object["relateditems"]:
            new_item = {
                "category": CATEGORIES[item]["key"],
                "icon": CATEGORIES[item]["icon"],
                "items": type_object["relateditems"][item],
            }
            type_object["relateditems"][item] = new_item

    # add form for creating a new collection in modal
    # collection_form = CollectionForm()

    # response = JsonResponse()

    # response["Access-Control-Allow-Origin"] = "*"

    return JsonResponse(
        {
            "success": True,
            "html": {
                "#search_result_modal_form": {
                    "html": render_to_string(
                        f"search-result-detail.html",
                        {
                            "object": type_object,
                            "type": type,
                            # 'manifest' : tmsViews.get_manifest_data(request, type, id),
                            # 'collection_form': collection_form,
                            "user": request.user,
                        },
                    ),
                },
                "#search_result_modal": {"action": "open"},
            },
        }
    )

    # return render(request, 'pages/'+view+'.html', {
    # 	'object': type_object,
    # 	'type': type,
    # 	'collection_form': collection_form
    # })
    # except:
    # 	raise Http404("There was an error getting this item")


def get_categories(request):
    categories = {
        "categories": [],
    }
    for category, fields in FIELDS_PER_CATEGORY.items():
        categories["categories"].append(
            {
                "fields": fields,
                "displaytext": CATEGORIES[category]["key"],
                "key": category,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "html": render_to_string(
                "search-advanced-accordion-category.html",
                {
                    "search": categories,
                },
            ),
        }
    )


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
        c = code.split(".")
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
    if "aggregations" in buckets:
        MET_aggregations = {
            k: v for k, v in buckets["aggregations"].items() if "MET" in k
        }
        if "MET" in MET_aggregations and MET_aggregations["MET"]["doc_count"] > 0:
            codes = {
                x["key"]: x["doc_count"]
                for x in MET_aggregations["MET"]["Codes"]["buckets"]
            }
            doc_counts = {
                x["key"]: x["doc_count"]
                for x in MET_aggregations["MET"]["Paths"]["buckets"]
            }
            if len(codes) and len(doc_counts):
                allCodes = {}

                # This private method collects the full path (code) to each term.
                # For example:
                # 	-	AAA_AAA_AAB requires [AAA, AAA_AAA]
                # 	-	AAA_AAB_AAF_AAB requires [AAA, AAA_AAB, AAA_AAB_AAF]
                def checkCode():
                    for k, v in codes.items():
                        fullCodes = getCodes(k.split("_")[:-1])
                        for code in fullCodes:
                            if code is not "" and code not in allCodes:
                                allCodes[code] = 0
                                # checkCode()
                        if k not in allCodes:
                            allCodes[k] = v

                checkCode()

                combined = [
                    {
                        "Code": k,
                        "Term": MET_lookup(code=k),
                        "Level": len(k.split("_")),
                        "Doc_count": doc_counts[MET_lookup(code=k).lower()]
                        if MET_lookup(code=k).lower() in doc_counts
                        else 0,
                    }
                    for k in allCodes.keys()
                ]

                def get_by_path(root, items):
                    return reduce(operator.getitem, items, root)

                def set_by_path(root, items, value):
                    get_by_path(root, items[:-1])[items[-1]] = {
                        "key": value[0],
                        "count": value[1],
                        "path": "_".join(items),
                    }

                di = {}

                # BUILD RECURSIVE TREE FOR TEMPLATE
                [
                    set_by_path(di, x["Code"].split("_"), (x["Term"], x["Doc_count"]))
                    for x in combined
                ]

                # SORT THE TREE FOR ALPHABETIC RENDERING ON TEMPLATE
                return combined, sorted(
                    di.items(), key=lambda k: operator.getitem(k[1], "key")
                )
    return {}, {}


def getCodes(code):
    return [
        "_".join(code[: idx + 1]) if len(code) > 1 else "".join(code[: idx + 1])
        for idx, c in enumerate(code)
    ]


def error(request, code):
    if code == 404:
        return render(request, "404.html")


####################################
###			SEARCH ROUTINE		 ###
####################################
def search_execute(request=None, dictionary=None):
    """
    This method prepares the base parameters for every search called. The method takes in Django WSGIRequest objects
    and dictionaries to extract all relevant fields. Crucial keys include:
    -	'category',
    -	'fields',
    -	'query',
    -	'MET',
    -	'facets',
    -	'result' with 'sort' and 'size' as well as 'pages.page'
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
    # 		BASE PARAMS		#
    #########################
    items = {"search": {}}
    items["user"] = request.user

    # A SEARCH POST IS SUBMITTED
    if type(request) is WSGIRequest:
        try:
            body = json.loads(request.body.decode("utf-8"))

            if request.method == "POST":

                (
                    items["search"]["query"],
                    items["search"]["category"],
                    items["search"]["fields"],
                ) = ("", "", {})

                # SIMPLE SEARCH
                if "query" in body:
                    items["search"]["query"] = body["query"]
                    
                # ADVANCED SEARCH
                else:

                    # ASSIGN CATEGORY
                    items["search"]["category"] = body['category']

                    # ASSIGN SEARCH FIELDS
                    items["search"]["fields"] = { SEARCH_FIELDS_PER_CATEGORY[items["search"]["category"]][k.split('_')[1]] : v for k, v in body.items() if len(v) > 0 and '_' in k and items["search"]["category"] in k}

                    # REFORMAT SEARCH PARAMETERS FROM ADVANCED SEARCH FORM
                    # { items['search']['fields'][x].update({ 'key' : SEARCH_FIELDS_PER_CATEGORY[items['search']['category']][y[0].split('_')[1]], 'val' : y[1], 'text' : FIELDS_PER_CATEGORY[items['search']['category']][SEARCH_FIELDS_PER_CATEGORY[items['search']['category']][y[0].split('_')[1]]] }) for x in items['search']['fields'] for y in list(request.POST.items()) if x == y[0].split('_')[0] and type(items['search']['fields'][x]) is dict and items['search']['category'] in x }
                    # {
                    #     items["search"]["fields"][x].update(
                    #         {
                    #             SEARCH_FIELDS_PER_CATEGORY[items["search"]["category"]][
                    #                 y[0].split("_")[1]
                    #             ]: y[1]
                    #         }
                    #     )
                    #     for x in items["search"]["fields"]
                    #     for y in list(body)
                    #     if x == y[0].split("_")[0]
                    #     and type(items["search"]["fields"][x]) is dict
                    #     and items["search"]["category"] in x
                    # }

                    # REMOVE IRRELEVANT FIELDS--REMOVE THIS AND UPDATE ABOVE LINE TO ENABLE CROSS-CATEGORY SEARCH
                    # items["search"]["fields"] = {
                    #     k: v
                    #     for k, v in body.items()
                    #     if type(v) is str
                    #     or (type(v) is dict and items["search"]["category"] in k)
                    # }

                    # items["search"]["fields"] = {
                    #     y: z
                    #     for k, v in {
                    #         k: v
                    #         for k, v in items["search"]["fields"].items()
                    #         if isinstance(v, dict)
                    #     }.items()
                    #     for y, z in v.items()
                    #     if z is not ""
                    # }

                # ADD MET
                items["search"]["MET"] = (
                    body["MET"]
                    if "MET" in body
                    else {"MET_tree": {}, "MET_paths": [], "MET_terms": []}
                )

                # FACETS
                items["search"]["facets"] = {}

                # EXTRACT FIELDS THAT WERE SEARCHED FOR
                items["search"]["result"] = {
                    "sort_options": [],
                    "sort": "",
                    "hits": [],
                    "size": 25,
                    "overall": 0,
                    "total": 20,
                    "params": [
                        {y: z}
                        for k, v in {
                            k: v
                            for k, v in items["search"]["fields"].items()
                            if isinstance(v, dict)
                        }.items()
                        for y, z in v.items()
                        if z is not ""
                    ],
                }

                # ADD STARTING PAGE
                items["search"]["result"]["pages"] = {
                    "page": 1,
                    "view_options": [10, 25, 50, 100],
                }
            else:

                # IF SEARCH PARAMETERS ALREADY EXIST IN THE REQUEST POST
                items["search"] = body
                # items['user'] = request.user
        except JSONDecodeError as e:
            print(e)
            items["search"]["result"] = []
            # items['search']['MET'] = { 'MET_tree' : [] }
            return items
    else:

        # RESOLVE A SEARCH TOKEN
        items["search"] = request["search"]

    # USER PROVIDED A SEARCH QUERY WITH COLON AND MAY BE LOOKING FOR A SPECIFIC OBJECT (E.G.: 'objects:HUMFA_27-5-1')
    if "query" in items["search"] and ":" in items["search"]["query"]:
        parts = items["search"]["query"].split(":")
        if parts[0] in CATEGORIES:
            items["search"]["category"] = parts[0]
            items["search"]["fields"]["allnumbers"] = parts[1]

    #########################
    # 	ADVANCED SEARCH		#
    #########################

    # USER DID A SIMPLE OR ADVANCED SEARCH
    else:

        # SEARCH CATEGORY IS SPECIFIED
        if items["search"]["category"]:

            items["search"]["result"]["sort_options"] = SORT_FIELDS_PER_CATEGORY[
                items["search"]["category"]
            ]

            # CHECK IF USER IS SEARCHING FOR DATE OR DATE RANGE
            if items["search"]["fields"]:
                dateRange = [
                    {"key": k, "value": v}
                    for k, v in items["search"]["fields"].items()
                    if "date" in k and v is not ""
                ]
                if len(dateRange):
                    for date in dateRange:
                        res = chkDate(date["value"])
                        if res[0] and not "_ms" in date["key"]:
                            items["search"]["fields"][f'{date["key"]}_ms'] = {}
                            items["search"]["fields"][f'{date["key"]}_ms'] = [
                                int(x[1]) for x in res[1]
                            ]
        else:
            # RETURN ALL EXCEPT LIBRARY DOC_TYPE
            items["search"]["ignore"] = "library"

    #########################
    # 	PROCESS SEARCH Q	#
    #########################
    items["search"], search_results = __execute(items["search"])

    #########################
    # 		SEPARATE	 	#
    #########################
    if "aggregations" in search_results:
        items["search"]["categories"] = [
            {
                "displaytext": CATEGORIES[x["key"]]["key"],
                "key": x["key"],
                "doc_count": x["doc_count"],
            }
            for x in search_results["aggregations"]["doc_types"]["buckets"]
        ]
        del search_results["aggregations"]["doc_types"]

    # IF SEARCH RESULTS
    if "hits" in search_results and "total" in search_results["hits"]:

        #  NO FACETS ARE YET SELECTED--THIS IS A VIRGIN SEARCH
        if not any(
            [
                y
                for v in items["search"]["facets"].values()
                for y in v
                if y["selected"] == True
            ]
        ):
            items["search"]["result"]["overall"] = search_results["hits"]["total"]

    #########################
    # 		COMPILE MET 	#
    #########################
    items["search"]["MET"]["MET_terms"], items["search"]["MET"]["MET_tree"] = build_MET(
        search_results
    )

    # EXTRACT SELECTED FACETS FROM ITEMS
    selected_facets = []
    if items["search"]["facets"]:
        selected_facets = list(find_val(items["search"]["facets"], True))

        # CHECK IF THE USER REQUIRES A SLIDER TO NAVIGATE DATES
        if "Dates" in items["search"]["facets"]:

            # GET MIN AND MAX VALS; NOTE: datetime OBJECT IS IN SECONDS
            dates = sorted(
                items["search"]["facets"]["Dates"], key=lambda x: x["display_text"]
            )
            for idx, x in enumerate(dates):
                dates[idx]["datetime"] = datetime(1970, 1, 1) + timedelta(
                    seconds=(float(f'{x["display_text"]}0000'))
                )

            items["search"]["result"]["date_slider"] = dates

    items["search"]["facets"] = {
        k: v
        for x in __recurse_aggs("", search_results, [], selected_facets)
        for k, v in x.items()
    }

    # APPEND TWENTY SEARCH RESULTS FOR DISPLAY
    items["search"]["result"]["total"] = (
        search_results["hits"]["total"]
        if search_results["hits"]["total"] <= 10000
        else 10000
    )
    items["search"]["result"]["hits"] = [
        {"id": hit.get("_id"), "type": hit.get("_type"), "source": hit.get("_source")}
        for hit in search_results["hits"]["hits"]
    ]

    # UPDATE PAGE DISPLAY RESULTS
    items["search"]["result"]["pages"].update(page_results(items["search"]))

    # CLEAN UP ITEMS OBJECT BEFORE RETURNING TO REQUEST
    del items["search"]["base"]
    del items["search"]["aggs"]
    del items["search"]["post"]

    return items


####################################
###			QUERY BUILDING		 ###
####################################
def __execute(items):
    """This function calls all methods to construct and execute the search query
    Once the query has been constructed from __base_query, __post_filter, and __build_aggregations
    the method returns the ElasticSearch query results.
    """
    items = __base_query(items)  # BUILD NORMAL BASE JSON QUERY
    items = __post_filter(items)  # BUILD POST FILTER
    items = __build_aggregations(items)  # AGGREGATE RELATED CATEGORIES AND FACETS

    # addToClipBoard(json.dumps(__build_query(items)))		# DEBUGGING ELASTICSEARCH QUERY

    return items, __search_get_results(__build_query(items))


def __search_get_results(query):
    """This private function executes the query to collect all search results from ES.
    These results include all aggregated results, MET, facets and otherwise.
    """
    return es.search(index=ES_INDEX, body=query)


def __build_query(items):
    """
    This method builds the body of the query that is sent to ElasticSearch. We are looking to return results
    starting at 0. Size is defined by the overall size. Overall size is determined before the user is able to manipulate
    results by toggling facets or MET terms. The base query is defined by the search terms, given through the forms.
    Aggregations are based on search terms, facets and MET terms; the post_filter is based on facets and MET terms.
    ###Parameters
    - items : dict
            - Dictionary with all search parameters
    ###Returns
    - Dictionary with constructed search query
    """
    q = {
        "from": (items["result"]["pages"]["page"] - 1) * items["result"]["size"],
        "size": items["result"]["size"],
        "query": items["base"],
        "aggregations": items["aggs"],
        "post_filter": items["post"],
        "sort": __sort_results(items),
    }
    return q


def __sort_results(items):
    if (
        not items["result"]["sort"] is ""
        and items["result"]["sort"] in SORT_FIELDS_PER_CATEGORY[items["category"]]
    ):
        return [
            {
                f'{items["result"]["sort_options"][items["result"]["sort"]]}': {
                    "order": "asc"
                }
            },
            {"_score": {"order": "asc"}},
        ]
    else:
        return [{"_score": {"order": "asc"}}]


def __bool_must_match(key, value, q):
    """
    This method appends 'match' queries to the 'must' list in the base_query
    """
    if len(value):
        b = {
            "bool": {
                "must": [
                    {
                        "match": {
                            key: {
                                "query": value.pop(0),
                            },
                        },
                    },
                ],
            },
        }
        q.update(b) if type(q) is dict else q.append(b)
        return (
            __bool_must_match(key, value, q["bool"]["must"])
            if type(q) is dict
            else __bool_must_match(key, value, q)
        )
    return q


def __base_query(items):
    """This private method builds the ElasticSearch base query.
    ###Parameters
    - items : dict
            - A dictionary with all search_terms
    - facets : list of dicts
            - A list with dictionaries of facets
    ###Output
    - An updated dictionary with a 'base' property
    """
    items["base"] = {}
    must = []

    # IF NO SEARCH TERM OR FIELDS ARE PROVIDED RETURN EVERYTHING IN DATABASE
    if not len(items["query"]) and not len(items["category"]):
        if "ignore" in items:
            items["base"]["bool"] = {
                "must": [],
                "must_not": [
                    {"query_string": {"default_field": "_type", "query": "library "}}
                ],
            }

    # CONSTRUCT A MUST-QUERY IF QUERY TERM IS PROVIDED (SIMPLE SEARCH)
    if len(items["query"]):
        must.append(__bool_must_match("_all", re.split("\W+", items["query"]), {}))
        items["base"]["bool"] = {"must": must}

    # CONSTRUCT A MUST-QUERY IF A CATEGORY IS SPECIFIED (ADVANCED SEARCH)
    if items["category"]:

        field = "_"
        if "_ms" in items["fields"].keys():
            field = "entrydate_ms"

        fields = {k: v for k, v in items["fields"].items() if k != field.split("_")[0]}

        for k, v in fields.items():

            # RANGE MATCH IF THE SEARCH IS FOR A DATE (IN SECONDS)
            if "entrydate" in k:
                if "entrydate_ms" in k and len(v):
                    must.append({"match": {k: v[0]}}) if len(v) == 1 else must.append(
                        {
                            "range": {
                                k: {
                                    "gte": v[0],
                                    "lte": v[1],
                                },
                            },
                        }
                    )

            # NESTED QUERY
            elif k.count(".") >= 2:
                v = (
                    re.split(" |-\.", v)
                    if "provenance" in k or "description" in k or "transcription" in k
                    else [v]
                )
                q = {
                    "nested": {
                        "path": k.split(".")[0],
                        "query": {"bool": {"must": [__bool_must_match(k, v, {})]}},
                    }
                }
                must.append(q)
            else:
                v = (
                    re.split(" |-|\.", v)
                    if "provenance" in k
                    or "description" in k
                    or "transcription" in k
                    or "title" in k
                    else [v]
                )
                must.append(__bool_must_match(k, v, {}))

        items["base"]["bool"] = {"must": must}

        # INCLUDE MET TERMS
    if len(items["MET"]["MET_paths"]):
        for v in items["MET"]["MET_paths"]:
            q = {
                "nested": {
                    "path": "MET",
                    "query": {
                        "bool": {"must": [{"match": {"MET.Codes.keyword": v["code"]}}]}
                    },
                }
            }
            must.append(q)
        items["base"]["bool"] = {"must": must}

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
    items["aggs"] = {}

    # SIMPLE SEARCH USE-CASE
    # if not items['category']:
    # return items

    # AGGREGATE ALL FACETS REGISTERED FOR THE CURRENT DOCUMENT TYPE
    if items["category"]:
        items["aggs"] = {
            name: term_agg
            for name, term_agg in list(FACETS_PER_CATEGORY[items["category"]].items())
        }

        # LIMIT MET AGGREGATIONS TO SELECTED CATEGORY
        if "MET" in items["aggs"]:
            q = {
                "inner": {
                    "filter": {
                        "bool": {"must": [{"match": {"type": items["category"]}}]}
                    }
                }
            }
            items["aggs"]["MET"]["aggregations"].update(q)

    # AGGREGATE ALL DATA TYPES IN THE DATA SET
    items["aggs"]["doc_types"] = {
        "terms": {"field": "_type", "exclude": "library", "size": 50}
    }

    return items


def __post_filter(items):
    """This private method builds an ElasticSearch boolean filter. The bool filter will be appended to
    the ElasticSearch query as well as individual facets to narrow results on the client to relevant
    facets by selected document type.
    ###Parameters
    - params : dict
            - A dictionary with all search_terms
    ###Output
    - A dictionary with all bool filters
    """
    items["post"] = {"bool": {}}
    must, should = [], []

    # LIMIT RETURNED RESULTS TO DOCUMENT TYPE (CATEGORY)
    if items["category"]:
        must.append({"type": {"value": items["category"]}})

        # ADD ENTRYDATES TO ENABLE FILTERING BY DATES
        if "entrydates_ms" in items["fields"].keys():
            must.append(
                {
                    "range": {
                        "entrydate_ms": {
                            "gte": items["fields"]["entrydates_ms"][0],
                            "lte": items["fields"]["entrydates_ms"][1],
                        }
                    }
                }
            )

    # INCLUDE FACETS
    if len(items["facets"]):

        # PROCESS SELECTED FACETS
        for facet_category in items["facets"].keys():
            selected_facets = [
                x for x in items["facets"][facet_category] if x["selected"] == True
            ]

            for facet in selected_facets:
                if facet_category in FACETS_PER_CATEGORY[items["category"]]:
                    field = list(
                        find_key(
                            "field",
                            FACETS_PER_CATEGORY[items["category"]][facet_category],
                        )
                    )[0]
                    if (
                        "nested"
                        in FACETS_PER_CATEGORY[items["category"]][facet_category]
                    ):
                        path = FACETS_PER_CATEGORY[items["category"]][facet_category][
                            "nested"
                        ]["path"]
                        should.append(
                            {
                                "nested": {
                                    "path": path,
                                    "query": {"term": {field: facet["display_text"]}},
                                }
                            }
                        )
                    else:
                        should.append({"term": {field: facet["display_text"]}})

    must.append({"bool": {"should": should}})

    # ASSIGNING THE FILTER ON THE ITEMS DICTIONARY TO BE PROCESSED IN THE QUERY
    items["post"]["bool"] = {"must": must}

    return items


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

    if "aggregations" not in search_results:
        facet_array = []
        if "buckets" in search_results:
            for bucket in search_results["buckets"]:
                if bucket["key"] and bucket["doc_count"]:
                    agg = {
                        "display_text": str(bucket["key"]),
                        "doc_count": bucket["doc_count"],
                        "selected": True
                        if any(
                            [
                                x
                                for x in selected_facets
                                for y in x.values()
                                if str(y) == str(bucket["key"])
                            ]
                        )
                        else False,
                    }
                    facet_array.append(agg)
            if agg_name in selected_facets:
                facets.insert(0, {agg_name: facet_array})
            else:
                facets.append({agg_name: facet_array})
            return facets
        else:
            for agg_name, value in list(search_results.items()):
                __recurse_aggs(agg_name, value, facets, selected_facets)
            return facets
    else:
        for agg_name, value in list(search_results["aggregations"].items()):
            if agg_name != "code" and agg_name != "paths":
                __recurse_aggs(agg_name, value, facets, selected_facets)
        return facets


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


def find_val(data, value):
    if isinstance(data, dict):
        for k, v in data.items():
            if v == value and isinstance(v, bool):
                yield k, v
            else:
                yield from find_val(v, value)
    if isinstance(data, list):
        for x in data:
            if any([x for x in x.values() if isinstance(x, bool)]):
                yield x
            else:
                yield from find_val(x, value)


def addToClipBoard(text):
    os.system("echo " + text.strip() + "| clip")


####################################


####################################
###			PAGINATE RESULTS	 ###
####################################
def page_results(items):
    """This method computes page ranges and page options from the search results and the current page displayed in the browers
    ###PARAMETERS
    total : int
            - The total number of hits returned from the ES search query
    page : int
            - The page currently displayed on the browser
    """
    pages = {
        "num_pages": (items["result"]["total"] // items["result"]["size"])
        + (items["result"]["total"] % items["result"]["size"] > 0)
    }  # CALCULATE NUMBER OF PAGES REQUIRED
    if pages["num_pages"] > 0:
        pages["range"] = __create_page_ranges(
            items["result"]["pages"]["page"], pages["num_pages"]
        )  # COMPUTE PAGES REQUIRED
    if items["result"]["pages"]["page"] > 1:
        pages["previous"] = (
            items["result"]["pages"]["page"] - 1
        )  # CHECK IF TEMPLATE NEEDS TO SHOW 'NEXT'
    if items["result"]["pages"]["page"] < pages["num_pages"]:
        pages["next"] = (
            items["result"]["pages"]["page"] + 1
        )  # CHECK IF TEMPLATE NEEDS TO SHOW 'PREVIOUS'
    return pages


def __create_page_ranges(page, num_pages):
    """This private method computes page ranges"""
    # create the range of page numbers and ellipses to show
    # always show 1. attempt to show two page numbers around the current page
    num_pages_range = [1]

    # check if we need an ellipsis after 1
    if page - 2 > 2:
        num_pages_range.append(-1)

    # determine values before
    if page - 2 <= 1:
        for i in range(2, page + 1):
            num_pages_range.append(i)
    else:
        for i in range(page - 2, page):
            num_pages_range.append(i)

    # add current page if it's not first or last
    if page != 1 and page != num_pages and page not in num_pages_range:
        num_pages_range.append(page)

    # determine values after
    if page + 2 >= num_pages:
        for i in range(page + 1, num_pages):
            num_pages_range.append(i)
    else:
        for i in range(page + 1, page + 3):
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
                    if (
                        dateRange[pos] is not ""
                        and any(char.isdigit() for char in dateRange[pos])
                        and len(dateRange[pos]) <= 2
                        and int(dateRange[pos]) <= 31
                    ):
                        addedDates.append(dateRange[pos])
                        dateRange.pop(pos)
                        return recurseArray(dateRange, pos)
                    else:
                        dateRange.pop(pos)
                        return recurseArray(dateRange, pos)

                # CHECK IF ADJACENT VALUES FORM A COHERENT DATE
                dateRange = values[idx - 3 : idx + 3]
                pos = dateRange.index(value)  # POSITION OF VALUE TO BE CHECKED
                dateRange = [
                    re.sub("[^-/0-9]", "", x) for x in dateRange
                ]  # CLEAN ARRAY VALUES
                year = "".join(
                    [
                        x
                        for x in dateRange
                        if all(char.isdigit() for char in x) and len(x) == 4
                    ]
                )

                if year:
                    dateRange.pop(dateRange.index(year))
                else:
                    # ASSUME YEAR BASED ON MOST COMMMON OCCURENCE IN CURRENT CONSTRUCTED DATES
                    year = "".join(
                        max(
                            set([k.split("/")[2] for k in dates.keys()]),
                            key=[k.split("/")[2] for k in dates.keys()].count,
                        )
                    )

                month = MONTHS.index(value.lower()) + 1

                day = ""

                dayOptions = recurseArray(dateRange, pos)

                if len(dayOptions) == 0:
                    day = "01"  # DEFAULT VALUE TO MAKE SEARCH WORK AND PROVIDE WIDEST RANGE
                elif len(dayOptions) == 1:
                    day = "".join(dayOptions)
                else:
                    print(
                        "multiple day options possible--have not yet come across a case like this, but have not extensively checked"
                    )
                    # if ()
                    # # WHICH OF THE DAY OPTIONS IS MOST REASONABLE?
                    # for dayOption in dayOptions:
                    #     distances = {}
                    #     string, ms = convertToMS(f'{dayOption}{month}{year}')
                    #     for date_ms in dates.values():
                    #         distances[string] = abs(ms - date_ms)

                    #     # GET LOWEST DISTANCE DIFFERENCE FROM DICT
                    #     lowest = min(distances, key=distances.get)

                value = f"{month}/{day}/{year}"

                string, ms = convertToMS(value)

                if string not in dates and ms < -870091200:
                    dates[string] = ms

            value = re.sub("[^-/0-9]", "", value)  # STRIP THE STRING OF ORDINALS

            if any(char.isdigit() for char in value):
                if len(value) <= 10:
                    values[idx] = value
                    if "-" in value or "/" in value:
                        splitVal = (
                            value.split("-")
                            if "-" in value
                            else (value.split("/") if "/" in value else [0, 0, 0])
                        )
                        if (
                            len(splitVal) == 3
                            and len(splitVal[2]) is 4
                            and int(splitVal[2]) > 1900 < 2000
                            and (
                                (int(splitVal[0]) <= 12 and int(splitVal[1]) <= 31)
                                or (int(splitVal[0]) <= 31 and int(splitVal[1]) <= 12)
                                or (int(splitVal[1]) <= 12 and int(splitVal[2]) <= 31)
                                or (int(splitVal[1]) <= 31 and int(splitVal[2]) <= 12)
                            )
                            and (
                                (int(splitVal[0]) < 2000 > 1890)
                                or (int(splitVal[1]) < 2000 > 1890)
                                or (int(splitVal[2]) < 2000 > 1890)
                            )
                        ):
                            if "-" in value:
                                value = value.split("-")
                                val = copy.deepcopy(value)
                                value[0] = val[1]
                                value[1] = val[0]
                                value = "/".join(value)

                            string, ms = convertToMS(value)
                            if ms < -870091200:
                                dates[string] = ms

                    # WE ASSUME VALUE IS A YEAR 'YYYY'
                    elif len(value) <= 4:
                        # DEFINE RANGE AS BEGINNING OF YEAR AND END OF YEAR
                        start = f"01/01/{value}"
                        end = f"12/31/{value}"
                        startStr, startMS = convertToMS(start)
                        endStr, endMS = convertToMS(end)
                        if startMS < -870091200:
                            dates[startStr] = startMS
                        if endMS < -870091200:
                            dates[endStr] = endMS
                else:
                    raise
        except:
            raise
    return dates


# THIS METHOD INTERPRETS A VERBAL DESCRIPTION OF A DATE PATTERN, MATCHING MONTH NAMES AGAINST A GLOBAL VARIABLE
# INPUTS: A STRING
# OUTPUTS: TUPLE WITH BOOLEAN FOR SUCCESS AND LIST OF DICTS WITH DATES (KEYS) AND MILLISECONDS (VALUES) SORTED FROM EARLY TO LATE
def chkDate(value):
    try:
        value = str(value)  # CHECK IF THE INPUT IS A STRING
        value = re.split("\W+", value)  # SPLIT ON SPACE ETC.

        # ITERATE OVER VALUES IN STRING LIST
        if len(value) > 0 and any([char.isdigit() for x in value for char in x]):
            dates = chkDatePattern(value)
        else:
            raise

        sorted_dates = sorted(dates.items(), key=operator.itemgetter(1))

        # REMOVE INTERMEDIATE VALUES OF RANGE
        if len(sorted_dates) > 2:
            sorted_dates = [sorted_dates[0], sorted_dates[-1]]

        return (True, sorted_dates)
    except:
        return (False, "There was an error parsing the date string")


def convertToMS(value):
    splitVal = value.split("/")
    splitVal = [f"0{x}" if len(x) < 2 and int(x) <= 9 else x for x in splitVal]

    if (
        len(splitVal) == 3
        and len(splitVal[0]) <= 2
        and len(splitVal[1]) <= 2
        and len(splitVal[2]) <= 4
    ):
        return (
            "/".join(splitVal),
            (parser().parse(value) - datetime(1970, 1, 1)).total_seconds(),
        )
    elif len(splitVal[0]) == 4:
        return value, (parser().parse(value) - datetime(1970, 1, 1)).total_seconds()
