import functools
import json
import logging

from django import http


log = logging.getLogger('pto')


def json_view(f):
    @functools.wraps(f)
    def wrapper(*args, **kw):
        try:
            response = f(*args, **kw)
        except:
            log.exception('JSON EXCEPTION')
            raise
        if isinstance(response, http.HttpResponse):
            return response
        else:
            return http.HttpResponse(json.dumps(response),
                                     content_type='application/json')
    return wrapper
