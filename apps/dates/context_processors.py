import re

from django.conf import settings


uppercase = re.compile(r'[A-Z]')


def global_settings(request):
    context = {}
    for k in dir(settings):
        if uppercase.match(k[0]):
            context[k] = getattr(settings, k)
    return context
