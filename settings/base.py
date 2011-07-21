# Django settings file for a project based on the playdoh template.

import logging
import os
import socket

from django.utils.functional import lazy

# Make file paths relative to settings.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
path = lambda *a: os.path.join(ROOT, *a)

ROOT_PACKAGE = os.path.basename(ROOT)

# Is this a dev instance?
DEV = False

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {}  # See settings_local.

# Site ID is used by Django's Sites framework.
SITE_ID = 1


## Internationalization.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# The host currently running the site.  Only use this in code for good reason;
# the site is designed to run on a cluster and should continue to support that
HOSTNAME = socket.gethostname()

# The front end domain of the site. If you're not running on a cluster this
# might be the same as HOSTNAME but don't depend on that.  Use this when you
# need the real domain.
DOMAIN = HOSTNAME

# Full base URL for your main site including protocol.  No trailing slash.
#   Example: https://example.com
SITE_URL = 'http://%s' % DOMAIN

# paths for images, e.g. mozcdn.com/amo or '/static'
STATIC_URL = SITE_URL

# Gettext text domain
TEXT_DOMAIN = 'messages'
STANDALONE_DOMAINS = [TEXT_DOMAIN, 'javascript']
TOWER_KEYWORDS = {'_lazy': None}
TOWER_ADD_HEADERS = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-US'

## Accepted locales

# On dev instances, the list of accepted locales defaults to the contents of
# the `locale` directory.  A localizer can add their locale in the l10n
# repository (copy of which is checked out into `locale`) in order to start
# testing the localization on the dev server.
try:
    DEV_LANGUAGES = [
        loc.replace('_', '-') for loc in os.listdir(path('locale'))
        if os.path.isdir(path('locale', loc)) and loc != 'templates'
    ]
except OSError:
    DEV_LANGUAGES = ('en-US',)

# On stage/prod, the list of accepted locales is manually maintained.  Only
# locales whose localizers have signed off on their work should be listed here.
PROD_LANGUAGES = (
    'en-US',
)

def lazy_lang_url_map():
    from django.conf import settings
    langs = settings.DEV_LANGUAGES if settings.DEV else settings.PROD_LANGUAGES
    return dict([(i.lower(), i) for i in langs])

LANGUAGE_URL_MAP = lazy(lazy_lang_url_map, dict)()

# Override Django's built-in with our native names
def lazy_langs():
    from django.conf import settings
    from product_details import product_details
    langs = DEV_LANGUAGES if settings.DEV else PROD_LANGUAGES
    return dict([(lang.lower(), product_details.languages[lang]['native'])
                 for lang in langs])

# Where to store product details etc.
PROD_DETAILS_DIR = path('lib/product_details_json')

LANGUAGES = lazy(lazy_langs, dict)()

# Paths that don't require a locale code in the URL.
SUPPORTED_NONLOCALES = ['media']


## Media and templates.

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = path('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin-media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '1iz#v0m55@h26^m6hxk3a7at*h$qj_2a$juu1#nv50548j(x1v'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.csrf',
    'django.contrib.messages.context_processors.messages',

    'dates.context_processors.global_settings',
    'jingo_minify.helpers.build_ids',
)

TEMPLATE_DIRS = (
    path('templates'),
)

def JINJA_CONFIG():
    import jinja2
    from django.conf import settings
#    from caching.base import cache
    config = {'extensions': ['tower.template.i18n', 'jinja2.ext.do',
                             'jinja2.ext.with_', 'jinja2.ext.loopcontrols'],
              'finalize': lambda x: x if x is not None else ''}
#    if 'memcached' in cache.scheme and not settings.DEBUG:
        # We're passing the _cache object directly to jinja because
        # Django can't store binary directly; it enforces unicode on it.
        # Details: http://jinja.pocoo.org/2/documentation/api#bytecode-cache
        # and in the errors you get when you try it the other way.
#        bc = jinja2.MemcachedBytecodeCache(cache._cache,
#                                           "%sj2:" % settings.CACHE_PREFIX)
#        config['cache_size'] = -1 # Never clear the cache
#        config['bytecode_cache'] = bc
    return config

# Bundles is a dictionary of two dictionaries, css and js, which list css files
# and js files that can be bundled together by the minify app.
MINIFY_BUNDLES = {
    'css': {
        'global': (
            'css/style.css',
        ),
        'jquery_ui': (
            'css/libs/jquery_ui/redmond/jquery-ui-1.8.14.datepicker.autocomplete.css',
        ),
        'dates': (
            'css/dates/notify.css',
            'css/dates/hours.css',
        ),
        'dates.home': (
            'css/libs/fullcalendar.css',
            'css/dates/home.css',
        ),
        'dates.list': (
            'css/libs/datatable/css/demo_table.css',
        )
    },
    'js': {
        'global': (
            'js/libs/jquery-1.6.2.min.js',
            #'js/libs/jquery.ui.all.js',
            #'js/libs/format.js',
            #'js/pto/pto.js',
        ),
        'dates.home': (
            'js/libs/fullcalendar.min.js',
            'js/dates/home.js',
        ),
        'dates.hours': (
            'js/dates/hours.js',
        ),
        'jquery_ui': (
            'js/libs/jquery-ui-1.8.14.datepicker.autocomplete.min.js',
        ),
        'dates.notify': (
            'js/dates/notify.js',
        ),
        'dates.list': (
            'js/libs/jquery.dataTables.js',
            'js/dates/list.js',
        ),
    }
}


## Middlewares, apps, URL configs.

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'commonware.middleware.FrameOptionsHeader',
    'commonware.middleware.HidePasswordOnException',
)

ROOT_URLCONF = '%s.urls' % ROOT_PACKAGE

INSTALLED_APPS = (
    # Local apps
    'commons',  # Content common to most playdoh-based apps.
    'jingo_minify',
    #'tower',  # for ./manage.py extract (L10n)

    # We need this so the jsi18n view will pick up our locale directory.
    ROOT_PACKAGE,

    # Third-party apps
    'commonware.response.cookies',
    #'djcelery',
    'django_nose',

    # Django contrib apps
    'django.contrib.auth',
    'django_sha2',  # Load after auth to monkey-patch it.

    'django.contrib.contenttypes',
    'django.contrib.sessions',
    # 'django.contrib.sites',
    'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    # L10n
    'product_details',

    # apps/
    'dates',
    'users',
)

# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.
DOMAIN_METHODS = {
    'messages': [
        ('apps/**.py',
            'tower.management.commands.extract.extract_tower_python'),
        ('**/templates/**.html',
            'tower.management.commands.extract.extract_tower_template'),
    ],

    ## Use this if you have localizable HTML files:
    #'lhtml': [
    #    ('**/templates/**.lhtml',
    #        'tower.management.commands.extract.extract_tower_template'),
    #],

    ## Use this if you have localizable JS files:
    #'javascript': [
        # Make sure that this won't pull in strings from external libraries you
        # may use.
    #    ('media/js/**.js', 'javascript'),
    #],
}

# Path to Java. Used for compress_assets.
JAVA_BIN = '/usr/bin/java'

## Auth
PWD_ALGORITHM = 'bcrypt'  # fast but insecure alternative 'sha512'
HMAC_KEYS = {  # for bcrypt only
    '2011-07-18': 'cheeseballs',
}

## Sessioning
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

## Memcache
CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
CACHE_MIDDLEWARE_KEY_PREFIX = 'pto'

## Tests
TEST_RUNNER = 'test_utils.runner.RadicalTestSuiteRunner'

## Celery
#BROKER_HOST = 'localhost'
#BROKER_PORT = 5672
#BROKER_USER = 'playdoh'
#BROKER_PASSWORD = 'playdoh'
#BROKER_VHOST = 'playdoh'
#BROKER_CONNECTION_TIMEOUT = 0.1
#CELERY_RESULT_BACKEND = 'amqp'
#CELERY_IGNORE_RESULT = True

# Logging
LOG_LEVEL = logging.DEBUG
HAS_SYSLOG = False  # syslog is used if HAS_SYSLOG and NOT DEBUG.
# SYSLOG_TAG = "http_app_addons"
# SYSLOG_TAG2 = "http_app_addons2"
# SYSLOG_CSP = "http_app_addons_csp"
# See PEP 391 and log_settings.py for formatting help.  Each section of
# LOGGING will get merged into the corresponding section of
# log_settings.py. Handlers and log levels are set up automatically based
# on LOG_LEVEL and DEBUG unless you set them here.  Messages will not
# propagate through a logger unless propagate: True is set.
LOGGING_CONFIG = None
LOGGING = {
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'stream_to_console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        'djang.request': {'level': logging.INFO},
        'django_auth_ldap': {
            'handlers': ['stream_to_console'],
            'level': logging.DEBUG,
            #'propagate': True,
        },
    },
}

# TODO(Kumar) after upgrading Django, remove this! The above config will work.
#logging.basicConfig()
#logging.getLogger().setLevel(logging.INFO)

AUTH_PROFILE_MODULE = 'users.UserProfile'

LOGIN_URL = '/users/login/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_REDIRECT_URL = '/'

DEFAULT_DATE_FORMAT = '%A, %B %d, %Y'
WORK_DAY = 8  # hours

EMAIL_SUBJECT = 'PTO notification from %(first_name)s %(last_name)s'
EMAIL_SUBJECT_EDIT = 'PTO update from %(first_name)s %(last_name)s'
EMAIL_SIGNATURE = "The Mozilla PTO cruncher"
FALLBACK_TO_ADDRESS = 'karen@mozilla.com'

# People you're not allowed to notify additionally
EMAIL_BLACKLIST = (
  'all@mozilla.com',
  'all-mv@mozilla.com',
)

# People who get notifications every time
HR_MANAGERS = (
  'dportillo@mozilla.com',
  'karen@mozilla.com',
)

try:
    ## LDAP
    import ldap

    AUTHENTICATION_BACKENDS = (
       'users.email_auth_backend.EmailOrUsernameModelBackend',
       'users.auth.backends.MozillaLDAPBackend',
       'django.contrib.auth.backends.ModelBackend',
    )

    # these must be set in settings/local.py!
    AUTH_LDAP_SERVER_URI = ''
    #AUTH_LDAP_BIND_DN = ''
    #AUTH_LDAP_BIND_PASSWORD = ''

    AUTH_LDAP_START_TLS = True
    AUTH_LDAP_USER_ATTR_MAP = {
      "first_name": "givenName",
      "last_name": "sn",
      "email": "mail",
    }
    AUTH_LDAP_PROFILE_ATTR_MAP = {
        "manager": "manager",
        "office": "physicalDeliveryOfficeName",
    }
    from django_auth_ldap.config import LDAPSearch
    AUTH_LDAP_USER_SEARCH = LDAPSearch(
      "o=com,dc=mozilla",
      ldap.SCOPE_SUBTREE,
      "mail=%(user)s"
    )
    AUTH_LDAP_USER_DN_TEMPLATE = "mail=%(user)s,o=com,dc=mozilla"

except ImportError:
    AUTHENTICATION_BACKENDS = (
       'users.email_auth_backend.EmailOrUsernameModelBackend',
       'django.contrib.auth.backends.ModelBackend',
    )
