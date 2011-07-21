# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Mozilla Sheriff Duty.
#
# The Initial Developer of the Original Code is Mozilla Corporation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#    Peter Bengtsson <peterbe@mozilla.com>
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import logging
from django import http
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
import django.contrib.auth.views
from django.conf import settings
import jingo
import forms
from models import get_user_profile
from django.shortcuts import render_to_response as django_render_to_response
from dates.decorators import json_view
from utils import ldap_lookup

def login(request):
    # mostly copied from zamboni
    logout(request)

    from monkeypatch_template_engine import jinja_for_django as jfd
    django.contrib.auth.views.render_to_response = jfd
    r = django.contrib.auth.views.login(request,
                         template_name='users/login.html',
                         redirect_field_name=REDIRECT_FIELD_NAME,
                         authentication_form=forms.AuthenticationForm)

    if isinstance(r, http.HttpResponseRedirect):
        # Succsesful log in according to django. Now we do our checks. I do
        # the checks here instead of the form's clean() because I want to use
        # the messages framework and it's not available in the request there
        user = get_user_profile(request.user)
        rememberme = request.POST.get('rememberme', None)
        if rememberme:
            request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            logging.debug((u'User (%s) logged in successfully with '
                                        '"remember me" set') % user)

    return r


def logout(request):
    django.contrib.auth.views.render_to_response = django_render_to_response
    django.contrib.auth.views.logout(request)
    #if 'to' in request.GET:
    #    request = _clean_next_url(request)
    next = request.GET.get('next') or settings.LOGOUT_REDIRECT_URL
    response = http.HttpResponseRedirect(next)
    return response


@json_view
def ldap_search(request):
    if not request.user.is_authenticated():
        return http.HttpResponseForbidden('Must be logged in')
    query = request.GET.get('term').strip()
    if len(query) < 2:
        return []

    results = []
    for each in ldap_lookup.search_users(query, autocomplete=True, limit=10):
        full_name_and_email = '%s %s <%s>' % (each['givenName'],
                                              each['sn'],
                                              each['mail'])
        result = {'id': each['uid'],
                  'label': full_name_and_email,
                  'value': full_name_and_email}
        results.append(result)
    return results
