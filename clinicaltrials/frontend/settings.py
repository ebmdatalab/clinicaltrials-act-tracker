"""
Django settings for clinicaltrials project.

Generated by 'django-admin startproject' using Django 1.10.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""
import logging
import os
import datetime

import common.utils

import custom_logging

logging.custom_handlers = custom_logging

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT = os.path.join(PROJECT_ROOT, "../static")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.10/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = common.utils.get_env_setting("CLINICALTRIALS_SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
CLINICALTRIALS_DEBUG = common.utils.get_env_setting("CLINICALTRIALS_DEBUG")
assert CLINICALTRIALS_DEBUG in ["yes", "no"], "CLINICALTRIALS_DEBUG was '{}'".format(
    CLINICALTRIALS_DEBUG
)
DEBUG = CLINICALTRIALS_DEBUG == "yes"


ALLOWED_HOSTS = ["*"]


# Parameters

GOOGLE_TRACKING_ID = common.utils.get_env_setting("CLINICALTRIALS_GOOGLE_TRACKING_ID")


# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sitemaps",
    "django.contrib.staticfiles",
    "compressor",
    "rest_framework",
    "django_filters",
    "frontend",
    "clinicaltrials",
    "django_extensions",
]

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly"
    ],
    "DEFAULT_PAGINATION_CLASS": "frontend.custom_rest_backends.DataTablesPagination",
    "SEARCH_PARAM": "search[value]",
    "DEFAULT_FILTER_BACKENDS": (
        "frontend.custom_rest_backends.DataTablesOrderingFilter",
        "rest_framework.filters.SearchFilter",
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework_csv.renderers.CSVRenderer",
    ),
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "heroku": {
            "format": (
                "%(asctime)s [%(process)d] [%(levelname)s] "
                + "pathname=%(pathname)s lineno=%(lineno)s "
                + "funcname=%(funcName)s %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "filters": {"require_debug_false": {"()": "django.utils.log.RequireDebugFalse"}},
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "heroku",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "applogfile": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(PROJECT_ROOT, "clinicaltrials.log"),
            "maxBytes": 1024 * 1024 * 50,  # 50MB
            "backupCount": 10,
            "formatter": "heroku",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["mail_admins", "console"],
            "level": "ERROR",
            "propagate": True,
        },
        "": {"handlers": ["applogfile"], "level": "INFO", "propagate": True},
    },
}

ADMINS = [("Seb", "seb.bacon@gmail.com")]  # XXX change to tech@ebmdatalab.net on launch

ROOT_URLCONF = "frontend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "frontend.context_processors.google_tracking_id",
                "frontend.context_processors.latest_date",
                "frontend.context_processors.next_planned_update",
                "frontend.context_processors.fine_per_day",
            ]
        },
    }
]

COMPRESS_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)

COMPRESS_ROOT = "static"

COMPRESS_CSS_FILTERS = [
    "compressor.filters.css_default.CssAbsoluteFilter",
    "compressor.filters.cssmin.CSSCompressorFilter",
]

COMPRESS_ENABLED = True
COMPRESS_OFFLINE = True

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
)


# Database
# https://docs.djangoproject.com/en/1.10/ref/settings/#databases

if "GAE_SERVICE" in os.environ:
    # Running on production App Engine, so connect to Google Cloud SQL using
    # the unix socket at /cloudsql/<your-cloudsql-connection string>
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "HOST": "/cloudsql/ebmdatalab:europe-west1:general-purpose-1",
            "NAME": common.utils.get_env_setting("CLINICALTRIALS_DB"),
            "USER": common.utils.get_env_setting("CLINICALTRIALS_DB_NAME"),
            "PASSWORD": common.utils.get_env_setting("CLINICALTRIALS_DB_PASS"),
        }
    }
else:
    # Running locally so connect to either a local postgres instance or connect to
    # Cloud SQL via the proxy. To start the proxy via command line:
    #
    #     $ cloud_sql_proxy -instances=[INSTANCE_CONNECTION_NAME]=tcp:3306
    #
    # See https://cloud.google.com/sql/docs/mysql-connect-proxy
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": common.utils.get_env_setting("CLINICALTRIALS_DB"),
            "USER": common.utils.get_env_setting("CLINICALTRIALS_DB_NAME"),
            "PASSWORD": common.utils.get_env_setting("CLINICALTRIALS_DB_PASS"),
            "HOST": "localhost",
            "CONN_MAX_AGE": 0,  # Must be zero, see api/view_utils#db_timeout
        }
    }


# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation."
        "UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation." "MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation." "CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation." "NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = "/static/"

# User stuff

LOGIN_REDIRECT_URL = "/"

NEXT_PLANNED_UPDATE = "2018-03-07"

# Default to next weekday if the previous constant is today or earlier
if NEXT_PLANNED_UPDATE <= datetime.date.today().strftime("%Y-%m-%d"):
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    if tomorrow.isoweekday() in set((6, 7)):
        tomorrow += datetime.timedelta(days=tomorrow.isoweekday() % 5)
    NEXT_PLANNED_UPDATE = tomorrow.strftime("%Y-%m-%d")

# Fine for each day a trial is late
# https://www.gpo.gov/fdsys/pkg/FR-2017-02-03/pdf/2017-02300.pdf
FINE_PER_DAY = 11569

BQ_PROJECT = "clinicaltrials"
BQ_HSCIC_DATASET = ""

# Twitter

TWITTER_CONSUMER_SECRET = common.utils.get_env_setting("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN_SECRET = common.utils.get_env_setting(
    "TWITTER_ACCESS_TOKEN_SECRET"
)

# Path to shell script of lines `export FOO=bar`. See environment-example for a sample.
PROCESSING_ENV_PATH = "/etc/profile.d/fdaaa_staging.sh"
PROCESSING_VENV_BIN = "/var/www/fdaaa_staging/venv/bin/"
PROCESSING_STORAGE_TABLE_NAME = "current_raw_json"

# Bucket in GCS to store data
STORAGE_PREFIX = "clinicaltrials/"
WORKING_VOLUME = "/mnt/volume-lon1-01/"  # should have at least 10GB space
WORKING_DIR = os.path.join(WORKING_VOLUME, STORAGE_PREFIX)
INTERMEDIATE_CSV_PATH = os.path.join(
    WORKING_VOLUME, STORAGE_PREFIX, "clinical_trials.csv"
)


HTTP_MANAGEMENT_SECRET = common.utils.get_env_setting(
    "CLINICALTRIALS_HTTP_MANAGEMENT_SECRET"
)
# List of commands it's OK to call through the web
HTTP_MANAGEMENT_WHITELIST = ["migrate", "process_data", "load_data"]
