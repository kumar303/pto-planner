from django.conf.urls.defaults import patterns, url
from django.views.decorators.cache import cache_page
from django.views.i18n import javascript_catalog


urlpatterns = patterns('pto.views',
    url(r'^$', 'home', name='pto.home'),
    url(r'^calculate_pto\.json$', 'calculate_pto', name='pto.calculate_pto'),

    # Javascript translations.
    url('^jsi18n.js$', cache_page(60 * 60 * 24 * 365)(javascript_catalog),
        {'domain': 'javascript', 'packages': ['pto']}, name='jsi18n'),
)
