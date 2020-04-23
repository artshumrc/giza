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

from .forms import CustomUserCreationForm


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
