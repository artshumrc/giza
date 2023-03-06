"""
Django settings for giza project.

Generated by 'django-admin startproject' using Django 1.10.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""

import os
import environ
from django.core.exceptions import ImproperlyConfigured

env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("DJANGO_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", True)

ALLOWED_HOSTS = [
    'localhost',
    'giza-web2.rc.fas.harvard.edu',
    'giza.fas.harvard.edu'
] + env.list("ALLOWED_HOSTS", default=[])


# Application definition
INSTALLED_APPS = [
    'search',
    'tms',
    'giza',
    'utils',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'giza.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            (os.path.join(BASE_DIR, 'templates')),
            (os.path.join(BASE_DIR, 'templates/layouts')),
            (os.path.join(BASE_DIR, 'templates/lessons')),
            (os.path.join(BASE_DIR, 'templates/my-giza')),
            (os.path.join(BASE_DIR, 'templates/pages')),
            (os.path.join(BASE_DIR, 'templates/partials')),
            (os.path.join(BASE_DIR, 'templates/search')),
            (os.path.join(BASE_DIR, 'templates/user-pages')),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'giza.context_processors.user_collections',
            ],
        },
    },
]

WSGI_APPLICATION = 'giza.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

DATABASES = {
    'default': env.db()
}

SEARCH_BACKENDS = {
    'default': {
        'BACKEND': 'elasticsearch',
        'URLS': [
            env('ELASTICSEARCH_CONTAINER_URL', default='http://localhost:9200')
        ],
        'INDEX': 'giza',
        'TIMEOUT': 5,
    },
    'iiif': {
        'BACKEND': 'elasticsearch',
        'URLS': [
            env('ELASTICSEARCH_CONTAINER_URL', default='http://localhost:9200')
        ],
        'INDEX': 'iiif',
        'TIMEOUT': 5,
    }
}

# Custom User and auth settings
# https://docs.djangoproject.com/en/3.0/ref/settings/#std:setting-LOGIN_URL
LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/collections/user'

# custom user model registration
AUTH_USER_MODEL = 'giza.CustomUser'

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

# NOTE: password validation is deactived for testing during development, readd when
# ready for production
"""

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
"""
AUTH_PASSWORD_VALIDATORS = []


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'http_static')
STATIC_URL = '/static/'
