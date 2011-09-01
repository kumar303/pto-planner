import re
import ldap
from ldap.filter import filter_format
from django.utils.encoding import smart_unicode
from django.conf import settings
from django.core.cache import cache
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django_auth_ldap.config import LDAPSearch


def _valid_email(value):
    try:
        validate_email(value)
        return True
    except ValidationError:
        return False

def fetch_user_details(email, force_refresh=False):
    cache_key = 'ldap_user_details_%s' % hash(email)
    if not force_refresh:
        result = cache.get(cache_key)
        if result is not None:
            #print "LDAP cache hit"
            return result
    #print "LDAP cache miss"

    results = search_users(email, 1)
    if results:
        result = results[0]
        #print result
        _expand_result(result)
        cache.set(cache_key, result, 60 * 60)
    else:
        result = {}
        # tell the cache to not bother again, for a while
        cache.set(cache_key, result, 60)

    return result


def search_users(query, limit, autocomplete=False):
    connection = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
    connection.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
    if limit > 0:
        connection.set_option(ldap.OPT_SIZELIMIT, limit)
    connection.simple_bind_s(settings.AUTH_LDAP_BIND_DN,
                             settings.AUTH_LDAP_BIND_PASSWORD)
    if autocomplete:
        filter_elems = []
        if query.startswith(':'):
            searches = {'uid': query[1:]}
        else:
            searches = {'givenName': query, 'sn': query, 'mail': query}
            if ' ' in query:
                # e.g. 'Peter b' or 'laura toms'
                searches['cn'] = query
        for key, value in searches.items():
            if not value:
                continue
            filter_elems.append(filter_format('(%s=%s*)',
                                              (key, value)))
        search_filter = ''.join(filter_elems)
        if len(filter_elems) > 1:
            search_filter = '(|%s)' % search_filter
    else:
        if '@' in query and _valid_email(query):
            search_filter = filter_format("(mail=%s)", (query, ))
        elif query.startswith(':'):
            search_filter = filter_format("(uid=%s)", (query[1:], ))
        else:
            search_filter = filter_format("(cn=*%s*)", (query, ))
    attrs = ['cn', 'sn', 'mail', 'givenName', 'uid']
    rs = connection.search_s("dc=mozilla", ldap.SCOPE_SUBTREE,
                            search_filter,
                            attrs)
    results = []
    for each in rs:
        result = each[1]
        _expand_result(result)
        results.append(result)
        if len(results) >= limit:
            break

    return results

def _expand_result(result):
    """
    Turn
      {'givenName': ['Peter'], ...
    Into
      {'givenName': u'Peter', ...
    """
    for key, value in result.items():
        if isinstance(value, list):
            if len(value) == 1:
                value = smart_unicode(value[0])
            elif not value:
                value = u''
            else:
                value = [smart_unicode(x) for x in value]
            result[key] = value
