"""
Django settings for blenderid project.

Generated by 'django-admin startproject' using Django 1.9.10.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import datetime
import pathlib
import pytz
from django.core.urlresolvers import reverse_lazy

BASE_DIR = pathlib.Path(__file__).absolute().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '-secret-'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = []
SITE_ID = 1

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'debug_toolbar',
    'oauth2_provider',
    'django_gravatar',
    'loginas',
    'bid_main',
    'bid_api',
    'bid_addon_support',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'oauth2_provider.middleware.OAuth2TokenMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'oauth2_provider.backends.OAuth2Backend',
    'django.contrib.auth.backends.ModelBackend',
]

ROOT_URLCONF = 'blenderid.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'bid_main.context_processors.settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'blenderid.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'database-name',
        'USER': 'username',
        'PASSWORD': 'password',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'CET'
DATE_FORMAT = 'd-b-Y (D)'
TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = f'd-b-Y, H:i'
SHORT_DATE_FORMAT = 'Y-m-d'
SHORT_DATETIME_FORMAT = f'{SHORT_DATE_FORMAT}, H:i'

USE_I18N = True

USE_L10N = False

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'webstatic']
STATIC_ROOT = BASE_DIR / 'static'

# Uploaded files
# https://docs.djangoproject.com/en/2.0/ref/settings/#std:setting-MEDIA_ROOT
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # may not be inside STATIC_ROOT

BLENDER_ID_ADDON_CLIENT_ID = '-secret-'

# Defining one of those means you have to define them all.
OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL = 'bid_main.OAuth2AccessToken'
OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL = 'bid_main.OAuth2RefreshToken'
OAUTH2_PROVIDER_APPLICATION_MODEL = 'bid_main.OAuth2Application'

OAUTH2_PROVIDER = {
    'SCOPES': {
        'email': 'Default scope',
    },

    'ALLOWED_REDIRECT_URI_SCHEMES': ['https'],
    'REQUEST_APPROVAL_PROMPT': 'auto',
    'ACCESS_TOKEN_EXPIRE_SECONDS': 3600 * 24 * 31,  # keep for a month
    'REFRESH_TOKEN_EXPIRE_SECONDS': 3600 * 24 * 31,  # keep for a month
    'ACCESS_TOKEN_MODEL': OAUTH2_PROVIDER_ACCESS_TOKEN_MODEL,
    'REFRESH_TOKEN_MODEL': OAUTH2_PROVIDER_REFRESH_TOKEN_MODEL,
    'APPLICATION_MODEL': OAUTH2_PROVIDER_APPLICATION_MODEL,
}

# This is required for compatibility with Blender Cloud, as it performs
# a POST request to /oauth/token.
APPEND_SLASH = False

# Read https://docs.djangoproject.com/en/1.9/topics/auth/passwords/#password-upgrading
# before removing any password hasher from this list.
PASSWORD_HASHERS = [
    'bid_main.hashers.BlenderIdPasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
]

AUTH_USER_MODEL = 'bid_main.User'
LOGIN_URL = 'bid_main:login'
LOGIN_REDIRECT_URL = 'bid_main:index'
LOGOUT_URL = reverse_lazy('bid_main:logout')

# Hosts that we allow redirecting to with a next=xxx parameter on the /login and /switch
# endpoints. This is a limited set for security reasons.
NEXT_REDIR_AFTER_LOGIN_ALLOWED_HOSTS = {
    'blender-cloud:5000', 'blender-cloud:5001',
    'cloud.blender.org', 'blender.cloud',
    'blender.community',
}

CSRF_FAILURE_VIEW = 'bid_main.views.errors.csrf_failure'


# Privacy Policy date; anyone who agreed to the privacy policy before this date
# (or never) will be presented with an agreement prompt and has to agree before
# being able to use the website.
PPDATE = datetime.datetime(2018, 5, 18, 0, 0, 0, tzinfo=pytz.utc)

BLENDER_MYDATA_BASE_URL = 'https://mydata.blender.org/'
