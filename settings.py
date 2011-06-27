# Django settings file for a project based on the playdoh template.

import logging
import os
import socket

from django.utils.functional import lazy

# Make file paths relative to settings.
ROOT = os.path.dirname(os.path.abspath(__file__))
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
USE_I18N = True

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

    'pto.context_processors.global_settings',
    'commons.context_processors.i18n',
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
        'pto': (
            'css/pto/jquery-ui-theme/ui.all.css',
            # Hmm, these files still get requested even though all.css
            # loads them?
            'css/pto/jquery-ui-theme/ui.theme.css',
            'css/pto/jquery-ui-theme/ui.core.css',
            'css/pto/jquery-ui-theme/ui.accordion.css',
            'css/pto/jquery-ui-theme/ui.datepicker.css',
            'css/pto/jquery-ui-theme/ui.dialog.css',
            'css/pto/jquery-ui-theme/ui.progressbar.css',
            'css/pto/jquery-ui-theme/ui.resizable.css',
            'css/pto/jquery-ui-theme/ui.slider.css',
            'css/pto/jquery-ui-theme/ui.tabs.css',
            'css/pto/main.css',
        ),
    },
    'js': {
        'pto': (
            'js/libs/jquery-1.4.4.min.js',
            'js/libs/jquery.ui.all.js',
            'js/libs/format.js',
            'js/pto/pto.js',
        ),
    }
}


## Middlewares, apps, URL configs.

MIDDLEWARE_CLASSES = (
    'commons.middleware.LocaleURLMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    'commonware.middleware.FrameOptionsHeader',
)

ROOT_URLCONF = '%s.urls' % ROOT_PACKAGE

INSTALLED_APPS = (
    # Local apps
    'commons',  # Content common to most playdoh-based apps.
    'jingo_minify',
    'tower',  # for ./manage.py extract (L10n)

    'examples',  # Example code. Can (and should) be removed for actual projects.

    # We need this so the jsi18n view will pick up our locale directory.
    ROOT_PACKAGE,

    # Third-party apps
    'commonware.response.cookies',
    'djcelery',
    'django_nose',

    # Django contrib apps
    'django.contrib.auth',
    'django_sha2',  # Load after auth to monkey-patch it.

    'django.contrib.contenttypes',
    # 'django.contrib.sessions',
    # 'django.contrib.sites',
    # 'django.contrib.messages',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    # L10n
    'product_details',

    'pto',
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
PWD_ALGORITHM = 'sha512'  # recommended: 'bcrypt'
HMAC_KEYS = {  # for bcrypt only
    #'2011-01-01': 'cheesecake',
}

## Tests
TEST_RUNNER = 'test_utils.runner.RadicalTestSuiteRunner'

## Celery
BROKER_HOST = 'localhost'
BROKER_PORT = 5672
BROKER_USER = 'playdoh'
BROKER_PASSWORD = 'playdoh'
BROKER_VHOST = 'playdoh'
BROKER_CONNECTION_TIMEOUT = 0.1
CELERY_RESULT_BACKEND = 'amqp'
CELERY_IGNORE_RESULT = True

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
    'loggers': {
        'pto': {'level': logging.INFO},
    },
}

# TODO(Kumar) after upgrading Django, remove this! The above config will work.
logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)
