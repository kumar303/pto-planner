import re
from urlparse import urlparse
import datetime
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import simplejson as json
from django.contrib.auth.models import User
from django.contrib.auth import REDIRECT_FIELD_NAME
from nose.tools import eq_, ok_

from mock import Mock

import ldap
from users.auth.backends import MozillaLDAPBackend
from users.utils.ldap_mock import MockLDAP


RaiseInvalidCredentials = object()

class UsersTest(TestCase):

    def setUp(self):
        super(UsersTest, self).setUp()
        # A must when code in this app relies on cache
        settings.CACHE_BACKEND = 'locmem:///'

        ldap.open = Mock('ldap.open')
        ldap.open.mock_returns = Mock('ldap_connection')
        ldap.set_option = Mock(return_value=None)

    def test_login_with_local_django_user(self):
        fake_user = [
          ('mail=mortal,o=com,dc=mozilla',
           {'cn': ['Peter Bengtsson'],
            'givenName': ['Pet\xc3\xa3r'], # utf-8 encoded
            'mail': ['peterbe@mozilla.com'],
            'sn': ['Bengtss\xc2\xa2n'],
            'uid': ['pbengtsson']
            })
        ]

        fake_user_plus = [
          ('mail=mortal,o=com,dc=mozilla',
           {'cn': ['Peter Bengtsson'],
            'givenName': ['Pet\xc3\xa3r'], # utf-8 encoded
            'mail': ['peterbe@mozilla.com'],
            'sn': ['Bengtss\xc2\xa2n'],
            'uid': ['pbengtsson'],
            'manager': ['mail=lthom@mozilla.com,dc=foo'],
            'physicalDeliveryOfficeName': ['London:::GB'],
            })
        ]

        ldap.initialize = Mock(return_value=MockLDAP({
          '(mail=mortal@mozilla.com)': 'anything',
          },
          credentials={
            'mail=mortal,o=com,dc=mozilla': 'secret',
          }))

        url = reverse('users.login')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        mortal = User.objects.create(
          username='mortal',
          first_name='Mortal',
          last_name='Joe'
        )
        mortal.set_password('secret')
        mortal.save()

        response = self.client.post(url, {'username': 'mortal',
                                          'password': 'wrong'})
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)

        response = self.client.post(url, {'username': 'mortal',
                                          'password': 'secret'})
        eq_(response.status_code, 302)
        path = urlparse(response['location']).path
        eq_(path, settings.LOGIN_REDIRECT_URL)

        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Mortal' in response.content)

        url = reverse('users.logout')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        path = urlparse(response['location']).path
        eq_(path, settings.LOGOUT_REDIRECT_URL)

        response = self.client.get('/')
        path = urlparse(response['location']).path
        eq_(path, settings.LOGIN_URL)
        eq_(response.status_code, 302)

        response = self.client.get(settings.LOGIN_URL)
        eq_(response.status_code, 200)
        ok_('Mortal' not in response.content)


    def test_login_with_ldap_user(self):
        fake_user = [
          ('mail=mortal,o=com,dc=mozilla',
           {'cn': ['Mortal Bengtsson'],
            'givenName': ['Mortal'],
            'mail': ['mortal@mozilla.com'],
            'sn': ['Bengtss\xc2\xa2n'],
            'uid': ['mortal'],
            })
        ]

        fake_user_plus = [
          ('mail=mortal,o=com,dc=mozilla',
           {'cn': ['Mortal Bengtsson'],
            'givenName': ['Mortal'],
            'mail': ['mortal@mozilla.com'],
            'sn': ['Bengtss\xc2\xa2n'],
            'uid': ['mortal'],
            'manager': ['mail=lthom@mozilla.com,dc=foo'],
            'physicalDeliveryOfficeName': ['London:::GB'],
            })
        ]

        ldap.initialize = Mock(return_value=MockLDAP({
          'mail=mortal@mozilla.com,o=com,dc=mozilla': fake_user,
          '(mail=mortal@mozilla.com)': fake_user_plus,
          },
          credentials={
            'mail=mortal@mozilla.com,o=com,dc=mozilla': 'secret',
          }))

        url = reverse('users.login')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.post(url, {'username': 'mortal@mozilla.com',
                                          'password': 'wrong'})
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)

        response = self.client.post(url, {'username': 'mortal@mozilla.com',
                                          'password': 'secret'})
        eq_(response.status_code, 302)
        path = urlparse(response['location']).path
        eq_(path, settings.LOGIN_REDIRECT_URL)

        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Mortal' in response.content)

        user, = User.objects.all()
        eq_(user.email, 'mortal@mozilla.com')
        eq_(user.username, 'mortal')
        eq_(user.first_name, u'Mortal')
        eq_(user.last_name, u'Bengtss\xa2n')

        profile = user.get_profile()
        eq_(profile.manager, 'lthom@mozilla.com')
        eq_(profile.office, u'London:::GB')
        eq_(profile.country, u'GB')
        eq_(profile.city, u'London')

        url = reverse('users.logout')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        path = urlparse(response['location']).path
        eq_(path, settings.LOGOUT_REDIRECT_URL)

        response = self.client.get('/')
        path = urlparse(response['location']).path
        eq_(path, settings.LOGIN_URL)
        eq_(response.status_code, 302)

        response = self.client.get(settings.LOGIN_URL)
        eq_(response.status_code, 200)
        ok_('Mortal' not in response.content)


    def _get_all_inputs(self, html):
        _input_regex = re.compile('<input (.*?)>', re.M | re.DOTALL)
        _attrs_regex = re.compile('(\w+)="([^"]+)"')
        all_attrs = {}
        for input in _input_regex.findall(html):
            attrs = dict(_attrs_regex.findall(input))
            all_attrs[attrs.get('name', attrs.get('id', ''))] = attrs
        return all_attrs

    def test_login_next_redirect(self):
        url = reverse('users.login')
        response = self.client.get(url, {'next': '/foo/bar'})
        eq_(response.status_code, 200)
        attrs = self._get_all_inputs(response.content)
        ok_(attrs[REDIRECT_FIELD_NAME])
        eq_(attrs[REDIRECT_FIELD_NAME]['value'], '/foo/bar')

        mortal = User.objects.create_user(
          'mortal', 'mortal', password='secret'
        )
        mortal.set_password('secret')
        mortal.save()

        response = self.client.post(url, {'username': 'mortal',
                                          'password': 'secret',
                                          'next': '/foo/bar'})
        eq_(response.status_code, 302)
        path = urlparse(response['location']).path
        eq_(path, '/foo/bar')

    def test_login_failure(self):
        ldap.initialize = Mock(return_value=MockLDAP({
          '(mail=mortal@mozilla.com)': 'anything',
          },
          credentials={
            'mail=mortal,o=com,dc=mozilla': 'secret',
          }))

        url = reverse('users.login')
        mortal = User.objects.create(
          username='mortal',
          first_name='Mortal',
          last_name='Joe',
          email='mortal@mozilla.com',
        )
        mortal.set_password('secret')
        mortal.save()

        response = self.client.post(url, {'username': 'mortal',
                                          'password': 'xxx'})
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)

        response = self.client.post(url, {'username': 'xxx',
                                          'password': 'secret'})
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)

    def test_login_rememberme(self):
        url = reverse('users.login')
        mortal = User.objects.create(
          username='mortal',
          first_name='Mortal',
          last_name='Joe'
        )
        mortal.set_password('secret')
        mortal.save()

        response = self.client.post(url, {'username': 'mortal',
                                          'password': 'secret',
                                          'rememberme': 'yes'})
        eq_(response.status_code, 302)
        expires = self.client.cookies['sessionid']['expires']
        date = expires.split()[1]
        then = datetime.datetime.strptime(date, '%d-%b-%Y')
        today = datetime.datetime.today()
        days = settings.SESSION_COOKIE_AGE / 24 / 3600
        eq_((then - today).days + 1, days)

    def test_login_by_email(self):
        url = reverse('users.login')

        mortal = User.objects.create(
          username='mortal',
          email='mortal@hotmail.com',
          first_name='Mortal',
          last_name='Joe'
        )
        mortal.set_password('secret')
        mortal.save()

        response = self.client.post(url, {'username': 'Mortal@hotmail.com',
                                          'password': 'secret'})
        eq_(response.status_code, 302)

        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Mortal' in response.content)

    def test_mozilla_ldap_backend_basic(self):
        back = MozillaLDAPBackend()
        class MockConnection:
            def __init__(self, mock_result):
                self.mock_result = mock_result
            def search_s(self, dn, scope, filter=None, attrs=None):
                return self.mock_result

        class LDAPUser:
            results = (['somedn', {
                  'uid': 'peter',
                  'givenName': 'Peter',
                  'sn': 'Bengtsson',
                  'mail': 'mail@peterbe.com',
                }],)
            def __init__(self, attrs):
                self.attrs = attrs

            def _get_connection(self):
                return MockConnection(self.results)

        ldap_user = LDAPUser({'mail':['mail@peterbe.com']})

        user, created = back.get_or_create_user('peter', ldap_user)

        ok_(created)
        ok_(user)
        eq_(user.username, 'peter')

        peppe = User.objects.create_user(
          'peppe',
          'mail@peterbe.com',
        )
        user, created = back.get_or_create_user('peter', ldap_user)
        ok_(not created)
        eq_(user, peppe)

        username = back.ldap_to_django_username('mail@peterbe.com')
        eq_(username, 'peppe')
        username = back.ldap_to_django_username('lois@peterbe.com')
        eq_(username, 'lois')

    def test_login_username_form_field(self):
        url = reverse('users.login')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        html = response.content.split('<form')[1].split('</form')[0]
        inputs = self._get_all_inputs(html)
        input = inputs['username']
        eq_(input['autocorrect'], 'off')
        eq_(input['spellcheck'], 'false')
        eq_(input['autocapitalize'], 'off')
        eq_(input['type'], 'email')

    def test_ldap_search(self):
        results = [
          ('mail=peter@mozilla.com,o=com,dc=mozilla',
           {'cn': ['Peter Bengtsson'],
            'givenName': ['Pet\xc3\xa3r'], # utf-8 encoded
            'mail': ['peterbe@mozilla.com'],
            'sn': ['Bengtss\xc2\xa2n'],
            'uid': ['pbengtsson']
            })
        ]

        ldap.initialize = Mock(return_value=MockLDAP({
          '(|(mail=peter*)(givenName=peter*)(sn=peter*))': results
        }))

        url = reverse('users.ldap_search')
        response = self.client.get(url, {'term': '  i  '})
        eq_(response.status_code, 403)

        mortal = User.objects.create(
          username='mortal',
          first_name='Mortal',
          last_name='Joe'
        )
        mortal.set_password('secret')
        mortal.save()
        assert self.client.login(username='mortal', password='secret')

        response = self.client.get(url, {'term': '  i  '})
        eq_(response.status_code, 200)
        ok_(response['content-type'].startswith('application/json'))


        response = self.client.get(url, {'term': 'peter'})
        eq_(response.status_code, 200)
        ok_(response['content-type'].startswith('application/json'))
        struct = json.loads(response.content)
        ok_(isinstance(struct, list))
        first_item = struct[0]

        label = '%s %s <%s>' % (u'Pet\xe3r',
                                u'Bengtss\xa2n',
                                'peterbe@mozilla.com')
        value = label
        eq_(first_item, {
          'id': 'pbengtsson',
          'label': label,
          'value': value,
        })
