import json
import uuid

from django import forms
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core import serializers
from django.http.response import Http404
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage, EmailMultiAlternatives, send_mail
from django.utils.html import strip_tags
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder
from django.views.decorators.csrf import ensure_csrf_cookie

from os.path import exists, join
import codecs

# from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group

# from django.contrib.auth.views import LogoutView
from django.contrib.auth.tokens import PasswordResetTokenGenerator

# from django.contrib.auth.forms import PasswordResetForm


# accounts/password_change/ [name='password_change']
# accounts/password_change/done/ [name='password_change_done']
# accounts/password_reset/ [name='password_reset']
# accounts/password_reset/done/ [name='password_reset_done']
# accounts/reset/<uidb64>/<token>/ [name='password_reset_confirm']
# accounts/reset/done/ [name='password_reset_complete']

# Django 2.2.24:
# from django.contrib.staticfiles.templatetags.staticfiles import static
from django.templatetags.static import static
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.urls import reverse, resolve
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from elasticsearch.exceptions import HTTP_EXCEPTIONS

from utils.elastic_backend import es, ES_INDEX
from utils.views_utils import CATEGORIES, FACETS_PER_CATEGORY, FIELDS_PER_CATEGORY, MET

from search.views import search_results, search_results_update, search_execute

from .forms import (
    CustomUserCreationForm,
    CollectionForm,
    CustomPasswordResetForm,
    CustomPasswordChangeForm,
)
from .models import Collection, CustomUser, Lesson, ElasticSearchItem, Search

RESULTS_SIZE = 20

# def build_es_query(search_term, fields):
#      if fields:
#           must = []
#           for k,v in list(fields.items()):
#                if v:
#                     must.append({
#                          "match" : {
#                               k : {
#                                    "query" : v,
#                                    "operator" : "and"
#                               }
#                          }
#                     })
#           q = {
#                "bool" : {
#                     "must" : must
#                }
#           }
#      elif search_term == '':
#           q = {
#                "match_all" : {}
#           }
#      else:
#           q = {
#                "bool" : {
#                 "should" : [
#                     {
#                        "match" : {
#                            "displaytext" : {
#                                "query" : search_term,
#                                "operator" : "and",
#                                "boost" : 2
#                            }
#                        }
#                     },
#                     {
#                          "match" : {
#                             "_all" : {
#                               "query" : search_term,
#                               "operator" : "and"
#                             }
#                          }
#                     }
#                 ]
#             }
#           }
#      return q

# def build_subfacet_aggs(current_category, current_subfacets, bool_filter):
#     if not current_category:
#         return {}
#     if current_category not in current_subfacets:
#         return { name : term_agg for name, term_agg in list(FACETS_PER_CATEGORY[current_category].items()) }

#     aggregations = {}
#     aggs_for_selected = {}
#     aggs_for_unselected = {}
#     should = []
#     # aggregations for a facet that has been selected by the user will only be affected by other selected facets
#     for name, term_agg in list(FACETS_PER_CATEGORY[current_category].items()):
#         if name in current_subfacets[current_category]:
#             # bool_filter_for_facet = build_bool(current_category, current_subfacets, name)
#             filter_name = name + "_selected_filter"
#             aggregations[filter_name] = {
#                 "filter" : {
#                     "bool" : bool_filter_for_facet
#                 },
#                 "aggregations": {
#                     name : term_agg
#                 }
#             }
#         else:
#             # other aggregations will be filtered by the selected facets
#             aggs_for_unselected[name] = term_agg

#     filter_name = "_".join(list(current_subfacets[current_category].keys())) + "_filter"

#     aggregations[filter_name] = {
#         "filter" : {
#             "bool" : bool_filter
#         },
#         "aggregations": aggs_for_unselected
#     }

#     return aggregations

# def recurse_aggs(agg_name, facets, sub_facets, facet_names):
#     if type(facets) != type(dict()):
#         return sub_facets

#     if 'aggregations' not in facets:
#         facet_array = []
#         if 'buckets' in facets:
#             for bucket in facets['buckets']:
#                 agg = {
#                 'display_text' : bucket['key'],
#                 'doc_count' : bucket['doc_count']
#                 }
#                 facet_array.append(agg)
#             if agg_name in facet_names:
#                 sub_facets.insert(0, {agg_name : facet_array})
#             else:
#                 sub_facets.append({agg_name : facet_array})
#             return sub_facets
#         else:
#             for agg_name, value in list(facets.items()):
#                 recurse_aggs(agg_name, value, sub_facets, facet_names)
#             return sub_facets
#     else:
#         for agg_name, value in list(facets['aggregations'].items()):
#             recurse_aggs(agg_name, value, sub_facets, facet_names)
#         return sub_facets

# def create_page_ranges(page, num_pages):
# 	# create the range of page numbers and ellipses to show
# 	# always show 1. attempt to show two page numbers around the current page
# 	num_pages_range = ["1"]

# 	# check if we need an ellipsis after 1
# 	if page - 2 > 2:
# 		num_pages_range.append('ellipsis')

# 	# determine values before
# 	if page - 2 <= 1:
# 		for i in range(2, page+1):
# 			num_pages_range.append(str(i))
# 	else:
# 		for i in range(page-2, page):
# 			num_pages_range.append(str(i))

# 	# add current page if it's not first or last
# 	if page != 1 and page != num_pages and str(page) not in num_pages_range:
# 		num_pages_range.append(str(page))

# 	# determine values after
# 	if page + 2 >= num_pages:
# 		for i in range(page+1, num_pages):
# 			num_pages_range.append(str(i))
# 	else:
# 		for i in range(page+1, page+3):
# 			num_pages_range.append(str(i))

# 	# check if we need an ellipsis before last page
# 	if page + 2 < num_pages - 1:
# 		num_pages_range.append('ellipsis')

# 	# always append last page, check it's not already in there (when there are only a few pages)
# 	if str(num_pages) not in num_pages_range:
# 		num_pages_range.append(str(num_pages))

# 	return num_pages_range


def giza_at_school(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string("gizaatschool.html"),
                },
            },
        }
    )


def common_topics(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string("commontopics.html"),
                },
            },
        }
    )


def faq(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string("faq.html"),
                },
            },
        }
    )


def giza_intro(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string("gizaintro.html"),
                },
            },
        }
    )


def giza_3d(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string("giza3d.html"),
                },
            },
        }
    )


def mygiza(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string(
                        "my-giza-landing.html",
                        {
                            "user": request.user,
                        },
                    ),
                },
            },
        }
    )


def about(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string("about.html"),
                },
            },
        }
    )


def archaeology(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string("archaeology.html"),
                },
            },
        }
    )


def contact(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string("contact.html"),
                },
            },
        }
    )


def sign_in(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        user = CustomUser.objects.get(email=data["username"])
        if user:
            if not user.is_active:
                body = render_to_string(
                    "user-registration-email.html",
                    {
                        "site_name": "Digital Giza",
                        "domain": get_current_site(request),
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "token": PasswordResetTokenGenerator().make_token(user=user),
                        "user": user,
                    },
                )
                # text = 'blabla'
                mail = EmailMultiAlternatives(
                    subject="Digital Giza account activation!",
                    from_email="uildriks.m@gmail.com",
                    to=[user.email],
                )
                # mail.content_subtype = 'html'
                mail.attach_alternative(body, "text/html")
                mail.send(fail_silently=False)
                # send_mail(subject="Digital Giza account activation!", message=body, from_email="uildriks.m@gmail.com", recipient_list=[user.email])
                return JsonResponse(
                    {
                        "success": True,
                        "html": {
                            "#sign_modal_form": {
                                "html": render_to_string(
                                    "user-registration-email-resent.html",
                                    {
                                        "user": user,
                                    },
                                ),
                            },
                        },
                    }
                )
            else:
                user = authenticate(
                    username=data["username"], password=data["password"]
                )
                login(request, user)
                return JsonResponse(
                    {
                        "success": True,
                        "html": {
                            "#header_bar": {
                                "html": render_to_string(
                                    "header.html",
                                    {
                                        "user": user,
                                    },
                                ),
                            },
                            "#sign_modal": {
                                "action": "close",
                            },
                        },
                    }
                )
        else:
            return JsonResponse(
                {
                    "success": True,
                    "html": {
                        "#sign_modal": {
                            "html": render_to_string(
                                "user-sign-in.html",
                                {
                                    "messages": "Uh-oh! We did not find a user with that username and password!"
                                },
                            ),
                            "action": "open",
                        },
                    },
                },
            )
    else:
        return JsonResponse(
            {
                "success": True,
                "html": {
                    "#sign_modal_form": {
                        "html": render_to_string("user-sign-in.html"),
                    },
                    "#sign_modal": {
                        "action": "open",
                    },
                },
            },
        )


def sign_up(request):
    """
    This route processes new sign up requests.
    """
    registered = False

    # RECEIVED A NEW REGISTRATION POST REQUEST
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        user = None
        user = CustomUserCreationForm(data=data)

        # IF CUSTOM USER FORM SUCCESSFULLY EVALUATES
        if user.is_valid():

            try:
                user = user.save()

                # ASSIGN THE CUSTOM USER TO A GROUP
                user.is_active = False
                user.first_name = user.full_name.split(" ")[0]
                user.last_name = user.full_name.split(" ")[-1]
                group = Group.objects.get_or_create(name="Public")
                if not group[1]:
                    group[0].save()
                user.groups.add(group[0])
                user.save()
                body = render_to_string(
                    "user-registration-email.html",
                    {
                        "site_name": "Digital Giza",
                        "domain": get_current_site(request),
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "token": PasswordResetTokenGenerator().make_token(user=user),
                        "user": user,
                    },
                )
                mail = EmailMessage(
                    "Digital Giza account activation!",
                    body,
                    "uildriks.m@gmail.com",
                    [user.email],
                )
                mail.content_subtype = "html"
                mail.send(fail_silently=False)
                return JsonResponse(
                    {
                        "success": True,
                        "html": {
                            "#sign_modal_form": {
                                "html": render_to_string(
                                    "user-registration-email-sent.html"
                                ),
                            },
                        },
                        # "modal": render_to_string("user-registration-email-sent.html"),
                        # "target": "sign_modal",
                        # "html": {
                        #     "header_bar": render_to_string("header.html", {"user": user}),
                        # },
                        # "modals": {
                        #     "sign_modal": {
                        #         "action": "close"
                        #     }
                        # }
                    }
                )
            except Exception as e:
                messages.add_message(request, messages.WARNING, e.args[0])
        else:
            if "email" in data:
                existing_user = CustomUser.objects.get(email=data["email"])
                if existing_user is not None and not existing_user.is_active:
                    body = render_to_string(
                        "user-registration-email.html",
                        {
                            "site_name": "Digital Giza",
                            "domain": get_current_site(request),
                            "uid": urlsafe_base64_encode(force_bytes(existing_user.pk)),
                            "token": PasswordResetTokenGenerator().make_token(
                                user=existing_user
                            ),
                            "user": existing_user,
                        },
                    )
                    mail = EmailMessage(
                        "Digital Giza account activation!",
                        body,
                        "uildriks.m@gmail.com",
                        [existing_user.email],
                    )
                    mail.content_subtype = "html"
                    mail.send(fail_silently=False)
                    return JsonResponse(
                        {
                            "success": True,
                            "html": {
                                "#sign_modal_form": {
                                    "html": render_to_string(
                                        "user-registration-email-resent.html",
                                        {
                                            "user": existing_user,
                                        },
                                    ),
                                },
                            },
                        },
                    )
                else:
                    messages.add_message(
                        request, messages.WARNING, user.errors)

            else:
                messages.add_message(request, messages.WARNING, user.errors)
    else:
        user = CustomUserCreationForm()

    return JsonResponse(
        {
            "success": True,
            "html": {
                "#sign_modal_form": {
                    "html": render_to_string(
                        "user-sign-up.html",
                        {
                            "messages": messages.get_messages(request)._queued_messages,
                            "custom_user_form": user,
                            "registered": registered,
                        },
                        request=request,
                    ),
                },
            },
        }
    )


def activate_account(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError):
        user = None

    generator = PasswordResetTokenGenerator()

    if user is not None and generator.check_token(user=user, token=token):
        user.is_active = True
        user.save()
        login(request, user)
        return HttpResponseRedirect("/", {user: user})
        # REDIRECT TO HOME-PAGE WITH USER SIGNED IN
        # return JsonResponse({"header": render_to_string("header.html", {"user": user})})
    else:
        # REMOVE USER DATA FROM DATABASE: TOKEN IS INVALID, RESEND LINK
        # REDIRECT TO HOME-PAGE WITH ERROR MESSAGE
        return JsonResponse({"header": render_to_string("header.html", {"user": user})})


@ensure_csrf_cookie
def index(request):
    return render(request, "index.html")


def home(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string("intro.html"),
                },
            },
        }
    )


def forgot_password(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        password_reset_form = CustomPasswordResetForm(data=data)
        try:
            # IF PASSWORD FORM WAS SUCCESSFULLY EVALUATED
            if password_reset_form.is_valid():

                # CHECK IF THE GIVEN EMAILADDRESS IS REGISTERED
                if list(password_reset_form.get_users(data["email"])):
                    user = list(
                        password_reset_form.get_users(data["email"]))[0]
                    token_generator = PasswordResetTokenGenerator()
                    token = token_generator.make_token(user=user)
                    try:
                        password_reset_form.send_mail(
                            subject_template_name="user-password-reset-subject-heading.txt",
                            email_template_name="user-reset-password-email.html",
                            context={
                                "site_name": "Digital Giza",
                                "protocol": "http",
                                "domain": "localhost:8000",
                                # 'uid' : 'a',
                                "token": token,
                            },
                            from_email="uildriks.m@gmail.com",
                            to_email=data["email"],
                        )
                        return JsonResponse(
                            {
                                "success": True,
                                "html": {
                                    "#sign_modal_form": {
                                        "html": render_to_string(
                                            "user-reset-password-email-sent.html",
                                            {
                                                "user": user,
                                            },
                                        ),
                                    },
                                },
                                # "modal": render_to_string(
                                #     "user-reset-password-email-sent.html",
                                #     {"user": user},
                                # ),
                                # "target": "sign_modal",
                            },
                        )
                    except:
                        messages.add_message(
                            request,
                            messages.WARNING,
                            "Your email is correct, but the server was unable to send you an email. Please contact Digital Giza staff.",
                        )
                        raise
                else:
                    messages.add_message(
                        request,
                        messages.WARNING,
                        "That email address is not in our database!",
                    )
                    raise
            else:
                messages.add_message(
                    request, messages.WARNING, password_reset_form.errors
                )
                raise
        except:
            l = messages.get_messages(request)._queued_messages

            # render
            context = {
                "messages": l,
                "form": password_reset_form,
            }
            return JsonResponse(
                {
                    "success": True,
                    "html": {
                        "#sign_modal_form": {
                            "html": render_to_string(
                                "user-reset-password.html", context, request=request
                            ),
                        },
                    },
                    # },
                    # "modal": render_to_string(
                    #     "user-reset-password.html", context, request=request
                    # ),
                    # "target": "sign_modal",
                },
            )
    else:
        password_reset_form = CustomPasswordResetForm()

    l = messages.get_messages(request)._queued_messages

    # render
    context = {
        "messages": l,
        "form": password_reset_form,
    }
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#sign_modal_form": {
                    "html": render_to_string(
                        "user-reset-password.html", context, request=request
                    ),
                },
            },
            # "modal": render_to_string(
            #     "user-reset-password.html", context, request=request
            # ),
            # "target": "sign_modal",
        },
    )

    # return JsonResponse(
    #     {
    #         "success": True,
    #         "html": render_to_string("user-reset-password.html")
    #     }
    # )


def change_password(request, token):
    if request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            user = CustomUser.objects.get(email=data["email"])
            if user:
                form = CustomPasswordChangeForm(user=user, data=data)
                if form.is_valid():
                    generator = PasswordResetTokenGenerator()
                    if generator.check_token(user, token):
                        user.is_active = True
                        user.save()
                        form.save()
                        update_session_auth_hash(request, form.user)
                        return JsonResponse(
                            {
                                "success": True,
                                "html": {
                                    "#header_bar": {
                                        "html": render_to_string(
                                            "header.html", {"user": user}
                                        ),
                                    },
                                    "#main_content": {
                                        "html": render_to_string(
                                            "user-reset-password-complete.html"
                                        ),
                                    },
                                },
                            }
                        )
                        # return render('index.html', { 'user' : user } )

                # if user is not None and default_token_generator.check_token(user, token):
                #     user.is_active = True
                #     user.save()

                return render(request, "index.html", {"user": request.user})
        except Exception as e:
            print(e)
            return render(request, "user-reset-password-complete.html")
    else:
        return render(
            request,
            "user-reset-password-new-password.html",
            {
                "validlink": True,
                "token": token,
                "form": CustomPasswordChangeForm(user=request.user),
            },
        )


def sign_out(request):
    logout(request)
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#header_bar": {
                    "html": render_to_string("header.html"),
                },
                "#main_content": {
                    "html": render_to_string("intro.html"),
                },
            },
        },
    )


################################
###         MY GIZA          ###
################################
@login_required
def my_giza(request, tab):
    """This user route returns all searches, collections and lessons stored for the logged in user
    The view takes a request and name of what the user is looking for, corresponding to the tabs on the my-giza.html page:
    - searches for search queries
    - collections for collections
    - lessons for lesson topics
    """
    return refresh_my_giza(request.user, tab)


def get_form(request, index=None, id=None, form=None):
    # print(index, id, form)
    if "collection_form" in form:
        return JsonResponse(
            {
                "success": True,
                "html": {
                    "#collection_modal_form": {
                        "html": render_to_string(
                            "search-details-add-to-my-giza-collection.html",
                            {
                                "user": request.user,
                                "collection_form": CollectionForm(),
                                "user_collections": __getPublicCollections(
                                    uid=request.user.id
                                ),
                                "index": index,
                                "id": id,
                            },
                        ),
                    },
                    "#collection_modal": {"action": "open"},
                },
            }
        )
        

def my_giza_add(request, tab, type=None, id=None, name=None):
    """This route adds new saved search queries, collections or lesson plans for the current user"""
    print(tab)

    # FORM FOR NEW SAVED SEARCH, COLLECTION OR LESSON PLAN IS REQUESTED
    if request.method == "GET":
        if "saved-search-queries" in tab:
            return JsonResponse(
                {
                    "success": True,
                    "html": {
                        "#save_search_modal_form": {
                            "html": render_to_string(
                                "my-giza-new-saved-search-query.html",
                                {
                                    "temp": {},
                                },
                            ),
                        },
                    },
                }
            )
            # return build_JsonResponse(True, "save_search_modal", {"temp": {}})
        #     if "collection" in tab:
        #         return JsonResponse(
        #             {
        #                 "success": True,
        #                 "modal": render_to_string(
        #                     "search-details-add-to-my-giza-collection.html",
        #                     {
        #                         "user": request.user,
        #                         "collection_form": CollectionForm(),
        #                         "user_collections": __getPublicCollections(
        #                             uid=request.user.id
        #                         ),
        #                         "type" : type,
        #                         "id" : id
        #                     },
        #                 ),
        #                 "target" : "collection_modal"
        #             }
        #         )

        if "collections" in tab:
            return JsonResponse(
                {
                    "success": True,
                    "html": {
                        "#collection_modal_form": {
                            "html": render_to_string(
                                "search-details-add-to-my-giza-collection.html",
                                {
                                    "tab": "collections",
                                    "collection_form": CollectionForm(),
                                    "type": "none",
                                    "id": "none",
                                },
                            ),
                        },
                    },
                }
            )
            # return build_JsonResponse(
            #     True,
            #     "collection_modal_form",
            #     {
            #         "tab": "collections",
            #         "type": "none",
            #         "id": "none",
            #         "collection_form": CollectionForm(),
            #     },
            # )

    # NEW SAVED SEARCH, COLLECTION OR LESSON PLAN IS POSTED
    else:
        try:
            # THIS IS A NEW COLLECTION
            if "collection" in tab and name is None:
                make_new_collection(request)
                return JsonResponse(
                    {
                        "success": True,
                        "html": {
                            "#collection_modal_form": {
                                "html": render_to_string(
                                    "search-details-add-to-my-giza-collection.html",
                                    {
                                        "user": request.user,
                                        "collection_form": CollectionForm(),
                                        "user_collections": __getPublicCollections(
                                            uid=request.user.id
                                        ),
                                        "type": type,
                                        "id": id
                                    },
                                ),
                            },
                            "#collection_modal": {"action": "open"},
                        }
                    }
                )
            elif 'collection' in tab and name is not None:
                add_to_collection(type, id, name)
                return JsonResponse(
                    {
                        "success": True,
                        "html": {
                            "#collection_modal_form": {
                                "html": render_to_string(
                                    "search-details-added-to-my-giza-collection.html",
                                    {
                                        "user": request.user,
                                        "collection": name,
                                        "type": type,
                                        "id": id
                                    },
                                ),
                            },
                            "#collection_modal": {"action": "open"},
                        }
                    }
                )
            if "collections" in tab:
                collections = __getPublicCollections()

                return JsonResponse(
                    {
                        "success": True,
                        "html": {
                            "#collection_modal_form": {
                                "html": render_to_string(
                                    "search-details-added-to-my-giza-collection.html",
                                    {
                                        "user": request.user,
                                        "collection": "collection",
                                        "type": type,
                                        "id": id
                                    },
                                ),
                            },
                            "#collection_modal": {"action": "open"},
                        }
                    }
                )

                # return JsonResponse(
                #     {
                #         "success": True,
                #         "html": {
                #             "#MyGizaDiv": {
                #                 "html": render_to_string(
                #                     "my-giza.html",
                #                     {
                #                         "collections": len(collections),
                #                         "MyGIZA-tab": render_to_string(
                #                             "mygiza-collections.html",
                #                             {
                #                                 "collections": __getPublicCollections(uid=request.user),
                #                                 "user": request.user,
                #                             },
                #                         ),
                #                     },
                #                 ),
                #             },
                #         },
                #     },
                # )
                # return build_JsonResponse(
                #     True,
                #     "MyGIZADiv",
                #     {
                #         "collections": len(collections),
                #         "MyGIZA-tab": render_to_string(
                #             "mygiza-collections.html",
                #             {"collections": collections, "user": request.user},
                #         ),
                #     },
                # )

                # return redirect('/collections/{}'.format(collection.slug)) # RETURN UUID?
        except Exception as e:
            print(e)

            # else:
            # messages.error(request, "Error creating collection.")

            # pass
            return refresh_my_giza(request.user, tab)


def make_new_collection(request):
    """" This method makes a new collection """
    try:
        collection_form = CollectionForm(
            data=json.loads(request.body.decode("utf-8")))
        if collection_form.is_valid():
            collection = collection_form.save()
            collection.owners.add(request.user)
            collection.save()
    except Exception as e:
        print(e)


def add_to_collection(type, id, name):
    """ This method adds a new object to a collection """
    try:
        collection = get_object_or_404(Collection, title=name)
        if collection:
            item = ElasticSearchItem(
                type=type, es_id=id, collection=collection)
            if item:
                item = item.save()
                collection.contents.add(item)
                collection.save()
    except Exception as e:
        print(e)


def refresh_my_giza(user, tab):
    searches = json.loads(
        serializers.serialize("json", __findSavedSearches(uid=user.id))
    )
    collections = json.loads(
        serializers.serialize("json", __getPublicCollections(uid=user.id))
    )

    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string(
                        "my-giza.html",
                        {
                            "tab": tab,
                            "searches_html": render_to_string(
                                "my-giza-tab-saved-search-queries.html",
                                {
                                    "searches": searches,
                                },
                            ),
                            # if "saved-search-queries" in tab
                            # else None,
                            "collections_html": render_to_string(
                                "my-giza-tab-collections.html",
                                {
                                    "collection_type": "public",
                                    "collections": collections,
                                },
                            ),
                            "searches": searches,
                            "collections": collections,
                            # if "collections" in tab
                            # else None,
                            "lessons_html": [] if "lessons" in tab else None,
                            "user": user,
                        },
                    ),
                },
            },
        },
    )
    # return render(request, )
    # return JsonResponse({ 'success' : True, 'html' : render_to_string('mygiza-saved-search-queries.html', { 'searches' : __findSavedSearches(user=request.user.id) }) })
    # return render(request, 'mygiza-saved-search-queries.html', { 'searches' : __findSavedSearches(user=request.user.id) })


# def my_giza_tab(request, tab):
#     """This user route returns the my-giza tab with the requested information to my-giza.html"""
#     query = __findSavedSearches(uid=request.user.id)
#     if "collectons" in tab:
#         query = (__getPublicCollections(uid=request.used.id),)
#     if "lessons" in tab:
#         query = []
#     print(tab)
#     term = "searches" if "saved-search-queries" in tab else tab
#     print(term)
#     return JsonResponse(
#         {
#             "success": True,
#             tab: query,
#             "html": {
#                 "#MyGIZAdiv": {
#                     "html": render_to_string(
#                         f"my-giza-tab-{tab}.html",
#                         {
#                             term: query,
#                         },
#                     ),
#                     ".modal.reveal": {"action": "close"},
#                 },
#             },
#             # "MyGIZA-tab": render_to_string(
#             #     f"my-giza-tab-{tab}.html",
#             #     {
#             #         term: query,
#             #     },
#             # ),
#         }
#     )


def searches_all(request):
    """This user route returns all searches stored for the logged in user as JSON"""
    return JsonResponse(
        {
            "success": True,
            "html": render_to_string(
                "#mygiza-saved-search-queries.html",
                {
                    "searches": __findSavedSearches(user=request.user.id),
                },
            ),
        }
    )


@login_required
def search_save(request):
    """This user route saves the user's current search parameters as a new Search model instance"""

    if "GET" in request.method:
        return JsonResponse(
            {
                "success": True,
                "html": {
                    "#saved_search_modal_form": {
                        "html": render_to_string("my-giza-new-saved-search-query.html"),
                    },
                    "#saved_search_modal": {
                        "action": "open",
                    },
                },
            },
        )
    else:
        try:
            name = json.loads(request.body.decode(
                "utf-8"))["saved_search_name"]
            search = json.loads(json.loads(
                request.body.decode("utf-8"))["search"])
            search["result"]["hits"] = []

            Search(owner=request.user.id, search=search, name=name).save()

            return JsonResponse(
                {
                    "success": True,
                    "html": {
                        "#saved_search_modal_form": {
                            "html": render_to_string(
                                "my-giza-new-saved-search-query-success.html"
                            ),
                        },
                        "#saved_search_modal": {
                            "action": "open",
                        },
                    },
                }
            )
        except Exception as e:
            print(e)


@login_required
def search_del(request, pk):
    """This user route deletes a single search by id"""
    searches = json.loads(
        serializers.serialize(
            "json",
            __findSavedSearches(
                uid=request.user.id,
                ssid=pk,
            ),
        )
    )
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#MyGIZAdiv": {
                    "html": render_to_string(
                        "my-giza-tab-saved-search-queries.html",
                        {
                            "searches": searches,
                            "total": len(searches),
                        },
                    )
                },
                ".modal.reveal": {"action": "close"},
            },
        }
    )


@login_required
def search_update(request):
    """This user route updates a single search by id"""
    if request.POST:
        return JsonResponse({"success": True, **__updateSavedSearch(request)})


def __updateSavedSearch(request):
    try:
        result = get_object_or_404(Search, id=request.POST.get("id"))
        if result:
            param = request.POST.get("param").split("_")
            if "category" in param:
                result[0]["search"]["category"].append(param[1])
            elif "query" in param:
                result.search["query"] = param[1]
            else:
                for facet in result.search["facets"][param[1]]:
                    if facet["display_text"] == param[2]:
                        facet["selected"] = False if facet["selected"] else True
            items = search_execute({"search": result.search})
            del items["search"]["result"]["hits"]
            result.search = items["search"]
            result.save(update_fields=["search"])

        return {"key": request.POST.get("id"), "search": result.search}
    except Http404:
        raise f'Search model {request.POST.get("id")} unknown'


def search_MET(request):
    if exists('search-MET.html'):
        html = codecs.open("search-MET.html", "r").read()
    else:
        html = render_to_string(
            "search-MET-a.html", {
                "MET_tree": MET
            })
        f = open("search-MET.html", "a")
        f.write(html)
        f.close()

    return JsonResponse(
        {
            "success": True,
            "html": html
        }
    )


def search_token(request):
    """This public route returns a single search redeemed by token"""
    try:
        if request.POST.get("token"):
            items = __findSavedSearches(ssid=request.POST.get("token"))
            if items:

                # RETURN IF TOKEN IS RESOLVED FROM SEARCH PAGE
                return (
                    JsonResponse(
                        {
                            "success": True,
                            "response": search_results_update(request, items),
                        }
                    ),
                )
            else:

                # RETURN IF NO RESULTS
                return JsonResponse(
                    {
                        "success": False,
                        "response": "No saved search found for that token",
                    }
                )
        else:

            # IF URL IS PASTED

            items = __findSavedSearches(ssid=request.GET.get("token"))

            if len(items) and len(items) == 1:
                return render(
                    request,
                    "search-results.html",
                    search_results_update(request, items[0]),
                )
            else:
                return JsonResponse(
                    {"success": False, "response": "You did not provide a valid token"}
                )
                # return render(request, 'pages/search-results.html', search_update(request, items))
            # RETURN IF NO TOKEN IS GIVEN
            # return redirect('/search/results')
            # return {'error' : "error"}

    # RETURN IF ERROR
    except:
        raise
        # return render(request, 'pages/search-results.html', {})


################################
### PRIVATE HELPER FUNCTIONS ###
################################
def __getPublicCollections(uid=None):
    """This method returns all public and user owned collections in JSON format"""
    return Collection.objects.filter(Q(owners=uid) | Q(public=True))


def __findSavedSearches(uid=None, ssid=None):
    """This private helper method finds saved searches for user id or search id"""
    """ If both are given, the record will be deleted """
    """ ### PARAMETERS """

    def complete(uid=None, ssid=None):
        return Search.objects.filter(Q(owner=uid) | Q(id=ssid))

    if uid and ssid:
        Search.objects.filter(Q(owner=uid) & Q(id=ssid)).delete()

    return complete(uid, ssid)

    # try:

    #     results = []
    #     if uid:
    #         results = Search.objects.filter(owner=uid)
    #     if ssid:
    #         results = Search.objects.filter(id=ssid)

    #     if uid and ssid:
    #         results.delete()
    #         results = Search.objects.filter(owner=uid)

    # if results:

    #     items = json.loads(serializers.serialize("json", results))

    #     # SERIALIZE DATA FOR TEMPLATE
    #     return [
    #         {
    #             "key": x["pk"],
    #             "name": x["fields"]["name"],
    #             "search": x["fields"]["search"],
    #         }
    #         for x in items
    #     ]

    # return {}
    #     return results
    # except:
    #     raise


################################
###         COLLECTIONS      ###
################################
""" COLLECTION FUNCTIONS
Collections are user stored groupings of random records. Collections
should probably store individual ElasticSearch record ids for quick retrieval.
"""


def collections_all(request):
    """This user route returns all collections stored for the logged in user"""
    return JsonResponse(
        {
            "success": True,
            "html": render_to_string(
                "mygiza-collections.html", {
                    "collections": __getPublicCollections()}
            ),
        }
    )


# @login_required
# def collections(request):
#     """ This user route returns all collections marked as public """
#     res = Collection.objects.filter(public=True)
#     return render(request, 'pages/mygiza-allcollections.html', { 'collections': res if res else [] })


def collections(request):
    """This public route returns all public collections"""
    collections = __getPublicCollections(uid=request.user.id)
    return JsonResponse(
        {"collections": serializers.serialize("json", list(collections))}
    )
    # saved_search_queries = __findSavedSearches(request.user.id)
    # return JsonResponse(
    #     {
    #         "success": True,
    #         "html": render_to_string(
    #             "my-giza.html",
    #             {
    #                 "collections": {
    #                     "collections": len(collections),
    #                     "html": render_to_string(
    #                         "mygiza-collections.html",
    #                         {
    #                             "collections": collections,
    #                             "user": request.user.is_authenticated,
    #                         },
    #                     ),
    #                 },
    #                 "user": request.user,
    #             },
    #         )
    #         # 'searches' : {
    #         # 'searches' : saved_search_queries,
    #         # 'html' : render_to_string('mygiza-saved-search-queries.html', {
    #         # 'searches' : saved_search_queries
    #         # })
    #         # }
    #     }
    # )


def collections_public(request):
    return JsonResponse({"success": True, "html": __getCollectionsView()})


@ login_required
def collections_private(request):
    return JsonResponse(
        {"success": True, "html": __getCollectionsView(request.user.id)}
    )


def __getCollectionsView(uid=None):
    """This private method returns the collections view either with public or user-specific collections as rendered HTML
    uid : int
        - The user id for which to retrieve all collections. If uid is None, the method returns all public collections
    """
    return render_to_string(
        "mygiza-collections-view.html",
        {
            "collections": Collection.objects.filter(owners=uid)
            if uid
            else Collection.objects.filter(public=True)
        },
    )


def collections_remove_item(request, cid, iid):
    collection = Collection.objects.get(id=cid)
    items = collection.contents.all()
    # REMOVE ID FROM COLLECTION.contents

    for item in items:
        if item.pk == iid:
            item.delete()

    collection = Collection.objects.get(id=cid)
    items = collection.contents.all()

    results = {'hits': []}

    for item in items:
        hit = {}
        hit.update({'type': item.type})
        hit.update({'id': item.es_id})
        hit.update({'es_id': item.pk})
        hit.update({'source': es.search("giza", item.type, body={
            "query": {"match": {"_id": item.es_id}}})['hits']['hits'][0]['_source']})
        # hit.update({ ''})
        results['hits'].append(hit)

    return JsonResponse(
        {
            "success": True,
            "html": {
                "#collection_modal_form": {
                    "html": render_to_string("my-giza-collection-edit.html", {
                        "collection": collection,
                        "search_result": results,
                        "user": request.user
                    }),
                },
                "#collection_modal": {"action": "open"},
            }
        }
    )


def edit_collection(request, token):
    """ This route opens the collection edit modal when a user selects a particular collection """
    collection = Collection.objects.get(id=token)
    items = collection.contents.all()

    results = {'hits': []}

    for item in items:
        hit = {}
        hit.update({'type': item.type})
        hit.update({'id': item.es_id})
        hit.update({'es_id': item.pk})
        hit.update({'source': es.search("giza", item.type, body={
            "query": {"match": {"_id": item.es_id}}})['hits']['hits'][0]['_source']})
        # hit.update({ ''})
        results['hits'].append(hit)

    return JsonResponse(
        {
            "success": True,
            "html": {
                "#collection_modal_form": {
                    "html": render_to_string("my-giza-collection-edit.html", {
                        "collection": collection,
                        "search_result": results,
                        "user": request.user
                    }),
                },
                "#collection_modal": {"action": "open"},
            }
        }
    )


@ login_required
def collection(request, slug):
    """This user route returns all items stored in a collection for the logged in user
    # PARAMETERS
    request : Django Request Object
    slug : str
        - Identifier of collection: is this not better a uuid?
    """

    collection = get_object_or_404(Collection, slug=slug)
    hits = []

    # search_term = request.GET.get('q', '')
    query = {}

    if collection.items.all():
        query = {
            "bool": {
                "should": [],
            }
        }
        for elasticsearch_item in collection.items.all():
            query["bool"]["should"].append(
                {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "_type": elasticsearch_item.type,
                                }
                            },
                            {
                                "term": {
                                    "_id": elasticsearch_item.es_id,
                                }
                            },
                        ]
                    }
                }
            )
    else:
        # pass a query that will get no values returned
        query = {"ids": {"type": "_doc", "values": []}}

    # categorystring = ""
    # current_category = request.GET.get('category', '')
    # current_subfacets = {}
    bool_filter = {
        "must": [],
    }
    sort = request.GET.get("sort", "_score")
    page = int(request.GET.get("page", 1))
    # results_from = 0
    # calculate elasticsearch's from, using the page value
    results_from = (page - 1) * RESULTS_SIZE
    # all_categories = {}
    # sub_facets = {}
    # has_next = False
    # has_previous = False
    # previous_page_number = 0
    # next_page_number = 0
    # num_pages_range = []
    # num_pages = 0
    # total = 0

    # body_query = {
    #     "from": results_from,
    #     "size": RESULTS_SIZE,
    #     "query": query,
    #     "aggregations": {
    #         "aggregation": {
    #             "terms": {
    #                 "field": "_type",
    #                 "exclude": "library", # ignore special type, library, which is used for the Digital Giza Library page
    #                 "size" : 50 # make sure to get all categories (rather than just 10)
    #             }
    #         }
    #     },
    #     "post_filter" : {
    #         "bool" : bool_filter
    #     },
    #     "sort" : sort
    # }

    # subfacet_aggs = build_subfacet_aggs(current_category, current_subfacets, bool_filter)
    # facets_for_category = es.search(index=ES_INDEX, body=body_query)

    # facet_names = []
    # if current_subfacets:
    #     for facet_name in list(current_subfacets[current_category].keys()):
    #         facet_names.append(facet_name)
    # rec = recurse_aggs('', facets_for_category, [], facet_names)
    # sub_facets[current_category] = rec

    search_results = es.search(
        index=ES_INDEX,
        body={
            "from": results_from,
            "size": 10000,
            "query": query,
            "aggregations": {
                "aggregation": {
                    "terms": {
                        "field": "_type",
                        # ignore special type, library, which is used for the Digital Giza Library page
                        "exclude": "library",
                        # make sure to get all categories (rather than just 10)
                        "size": 50,
                    }
                }
            },
            "post_filter": {"bool": bool_filter},
            "sort": sort,
        },
    )

    # all_categories['types'] = []
    # for count in search_results['aggregations']['aggregation']['buckets']:
    #      all_categories['types'].append({
    #         'key' : count['key'],
    #         'doc_count' : count['doc_count'],
    #         'display_text' : CATEGORIES[count['key']]
    #     })
    for hit in search_results["hits"]["hits"]:
        hits.append(
            {
                "id": hit.get("_id"),
                "type": hit.get("_type"),
                "source": hit.get("_source"),
            }
        )

    # total = search_results['hits']['total']

    # num_pages = (total // RESULTS_SIZE) + (total % RESULTS_SIZE > 0)
    # if num_pages > 0:
    #     num_pages_range = create_page_ranges(page, num_pages)

    # if page > 1:
    #     has_previous = True
    #     previous_page_number = page - 1
    # if page < num_pages:
    #     has_next = True
    #     next_page_number = page + 1

    # # combine the current_subfacets into strings for quick comparison in template
    # subfacet_strings = []
    # if current_category and current_category in current_subfacets:
    #     for facet_name, facet_values in list(current_subfacets[current_category].items()):
    #         for value in facet_values:
    #             subfacet_strings.append("%s_%s_%s" % (current_category, facet_name, value))

    # search_params = []
    # if search_term:
    #     search_params.append(('q', 'Keyword', search_term))
    # if current_category:
    #     for k, v in list(fields.items()):
    #         if v:
    #             search_params.append((current_category+'_'+k, FIELDS_PER_CATEGORY[current_category][k], v))

    return render(
        request,
        "mygiza-collection.html",
        {
            "collection": collection,
            # 'search_params' : search_params,
            "hits": hits,
            # 'sub_facets' : sub_facets,
            # 'current_subfacets' : current_subfacets,
            # 'subfacet_strings' : subfacet_strings,
            # 'total' : total,
            # 'has_previous' : has_previous,
            # 'previous_page_number' : previous_page_number,
            # 'has_next' : has_next,
            # 'next_page_number' : next_page_number,
            # 'num_pages_range' : num_pages_range,
            # 'num_pages' : num_pages,
        },
    )


def collections_create(request):

    # METHOD IS 'POST': NEW COLLECTION IS POSTED
    if request.method == "POST":
        collection_form = CollectionForm(data=request.POST)

        # save user
        if collection_form.is_valid():
            # ADD
            collection = collection_form.save()
            collection.owners.add(request.user)
            collection.save()

            collections = __getPublicCollections()

            return JsonResponse(
                {
                    "success": True,
                    "collections": {
                        "collections": len(collections),
                        "html": render_to_string(
                            "mygiza-collections.html",
                            {
                                "collections": collections,
                                "user": request.user.is_authenticated,
                            },
                        ),
                    },
                }
            )

            # return redirect('/collections/{}'.format(collection.slug)) # RETURN UUID?

        else:
            messages.error(request, "Error creating collection.")

    # METHOD IS 'GET': NEW COLLECTION IS BEING MADE
    else:
        return JsonResponse(
            {
                "success": True,
                "html": render_to_string(
                    "mygiza-collection-new.html",
                    {
                        "#collection_form": CollectionForm(),
                    },
                ),
            }
        )

    # return render(request, 'pages/mygiza-collection-edit.html', {
    #     'collection_form': collection_form,
    # })


# def add_to_collection(request):
#     if request.method == "GET":
#         pass
#     else:
#         pass


def collections_add(collection, type, id):
    """
    This route adds a record to a collection using the little '+' ico class
    """
    try:
        collection = Collection.objects.filter(
            id=uuid.UUID(collection)).first()
        elasticsearch_item = ElasticSearchItem(
            es_id=int(id),
            type=type,
            collection=collection,
        )
        elasticsearch_item.save()
        return JsonResponse(
            {
                "success": True,
                "response": f"You have added this record to collection {collection.title}",
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "response": "Something went wrong"})


def collections_delete(request, token):
    try:
        print(token)
        collection = Collection.objects.filter(
            Q(owners=request.user.id) & Q(id=token))
        collection.delete()
        # query = __getPublicCollections(uid=request.used.id)
        return refresh_my_giza(request.user, "collections")
        # return JsonResponse(
        # {
        # "success": True,
        # "collections": query,
        # "MyGIZA-tab": render_to_string(f"my-giza-tab-collections.html", {"collections" : query}),
        # }
    # )
    except Exception as e:
        print(e)


@ login_required
def collections_edit(request, id):
    print(id)

    # create a collection
    if request.method == "POST":
        collection_form = CollectionForm(data=request.POST)

        # save user
        if collection_form.is_valid():

            # create user
            collection = collection_form.save()
            collection.save()

            return redirect("/collections/{}".format(collection.slug))

        else:
            messages.error(request, "Error creating collection.")

    # show collection form
    else:
        collection = get_object_or_404(Collection, id=id)
        collection_form = CollectionForm(collection)

        # user does not own this collection, redirect to collections page
        if not request.user in collection.owners.all():
            return redirect("/collections/")

        # handle adding new item id and type to collection
        if request.GET.get("add_item_id") and request.GET.get("add_item_type"):
            elasticsearch_item = ElasticSearchItem(
                es_id=request.GET.get("add_item_id"),
                type=request.GET.get("add_item_type"),
                collection=collection,
            )
            elasticsearch_item.save()
            return redirect("/collections/{}".format(collection.id))

        elif request.GET.get("remove_item_id") and request.GET.get("remove_item_type"):
            elasticsearch_item = ElasticSearchItem.objects.filter(
                es_id=request.GET.get("remove_item_id"),
                type=request.GET.get("remove_item_type"),
                collection=collection,
            )
            elasticsearch_item.delete()
            return redirect("/collections/{}".format(collection.id))

    return render(
        request,
        "mygiza-collection-edit.html",
        {
            "#collection_form": collection_form,
        },
    )


@ login_required
def collection_view(request, id):
    collection = get_object_or_404(Collection, id=id)
    collection_form = CollectionForm(collection)
    return render(
        request,
        "mygiza-collection-edit.html",
        {
            "#collection_form": collection_form,
        },
    )


################################
###         LESSONS          ###
################################
def lessons(request):
    return JsonResponse(
        {
            "success": True,
            "html": {
                "#main_content": {
                    "html": render_to_string(
                        "lessons.html",
                        {
                            "lessons": Lesson.objects.all(),
                        },
                    ),
                }
            },
        }
    )


def lesson(request, pk):
    lesson = get_object_or_404(Lesson, pk=pk)
    lessons = Lesson.objects.all()

    return JsonResponse(
        {
            "success": True,
            "html": {
                "#lesson_modal_form": {
                    "html": render_to_string(
                        "lesson.html",
                        {
                            "lesson": lesson,
                            "lessons": lessons,
                        },
                    )
                },
                "#lesson_modal": {
                    "action": "open"
                }
            },
        }
    )
