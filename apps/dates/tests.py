import re
import time
from urlparse import urlparse
from collections import defaultdict
import datetime
from django.test import TestCase
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils import simplejson as json
from django.core import mail
from models import Entry, Hours
from nose.tools import eq_, ok_
from mock import Mock
import ldap
from users.utils.ldap_mock import MockLDAP


class TestUtils(TestCase):

    def test_get_weekday_dates(self):
        from dates.utils import get_weekday_dates
        d1 = datetime.date(2018, 1, 1)  # a Monday
        d2 = datetime.date(2018, 1, 9)  # next Tuesday
        dates = list(get_weekday_dates(d1, d2))
        eq_(dates[0].strftime('%A'), 'Monday')
        eq_(dates[1].strftime('%A'), 'Tuesday')
        eq_(dates[2].strftime('%A'), 'Wednesday')
        eq_(dates[3].strftime('%A'), 'Thursday')
        eq_(dates[4].strftime('%A'), 'Friday')
        eq_(dates[5].strftime('%A'), 'Monday')
        eq_(dates[6].strftime('%A'), 'Tuesday')

    def test_parse_datetime(self):
        from dates.utils import parse_datetime, DatetimeParseError
        eq_(parse_datetime('1285041600000').year, 2010)
        eq_(parse_datetime('1283140800').year, 2010)
        eq_(parse_datetime('1286744467.0').year, 2010)
        self.assertRaises(DatetimeParseError, parse_datetime, 'junk')


class ModelsTest(TestCase):

    def test_cascade_delete_entry(self):
        user = User.objects.create_user(
          'mortal', 'mortal', password='secret'
        )
        entry = Entry.objects.create(
          user=user,
          start=datetime.date.today(),
          end=datetime.date.today(),
          total_hours=8
        )

        Hours.objects.create(
          entry=entry,
          hours=8,
          date=datetime.date.today()
        )

        user2 = User.objects.create_user(
          'other', 'other@test.com', password='secret'
        )
        entry2 = Entry.objects.create(
          user=user2,
          start=datetime.date.today(),
          end=datetime.date.today(),
          total_hours=4
        )

        Hours.objects.create(
          entry=entry2,
          hours=4,
          date=datetime.date.today()
        )

        eq_(Hours.objects.all().count(), 2)
        entry.delete()
        eq_(Hours.objects.all().count(), 1)


class ViewsTest(TestCase):

    def setUp(self):
        super(ViewsTest, self).setUp()
        # A must when code in this app relies on cache
        settings.CACHE_BACKEND = 'locmem:///'

        ldap.open = Mock('ldap.open')
        ldap.open.mock_returns = Mock('ldap_connection')
        ldap.set_option = Mock(return_value=None)

        settings.HR_MANAGERS = ('boss@mozilla.com',)
        boss = [
          ('mail=boss@mozilla.com,o=com,dc=mozilla',
           {'cn': ['Hugo Boss'],
            'givenName': ['Hugo'],
            'mail': ['boss@mozilla.com'],
            'sn': ['Boss'],
            'uid': ['hugo'],
            })
        ]

        ldap.initialize = Mock(return_value=MockLDAP({
          '(mail=boss@mozilla.com)': boss,
          },
          credentials={
            settings.AUTH_LDAP_BIND_DN: settings.AUTH_LDAP_BIND_PASSWORD,
          }))

    def test_notify_basics(self):
        url = reverse('dates.notify')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        path = urlparse(response['location']).path
        eq_(path, settings.LOGIN_URL)

        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        peter.set_password('secret')
        peter.save()

        assert self.client.login(username='peter', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        monday = datetime.date(2018, 1, 1)  # I know this is a Monday
        wednesday = monday + datetime.timedelta(days=2)
        response = self.client.post(url, {'start': wednesday,
                                          'end': monday})
        eq_(response.status_code, 200)

        details = 'Going on a cruise'
        response = self.client.post(url, {'start': monday,
                                          'end': wednesday,
                                          'details': details})
        eq_(response.status_code, 302)

        entry, = Entry.objects.all()
        eq_(entry.user, peter)
        eq_(entry.start, monday)
        eq_(entry.end, wednesday)
        eq_(entry.total_hours, None)

        url = reverse('dates.hours', args=[entry.pk])
        eq_(urlparse(response['location']).path, url)

        response = self.client.get(url)
        eq_(response.status_code, 200)

        # expect an estimate of the total number of hours
        ok_(str(3 * settings.WORK_DAY) in response.content)

        # you can expect to see every date laid out
        ok_(monday.strftime(settings.DEFAULT_DATE_FORMAT) in response.content)
        tuesday = monday + datetime.timedelta(days=1)
        ok_(tuesday.strftime(settings.DEFAULT_DATE_FORMAT) in response.content)
        ok_(wednesday.strftime(settings.DEFAULT_DATE_FORMAT) in response.content)

        # check that the default WORK_DAY radio inputs are checked
        radio_inputs = self._get_inputs(response.content, type="radio")
        for name, attrs in radio_inputs.items():
            if attrs['value'] == str(settings.WORK_DAY):
                ok_(attrs['checked'])
            else:
                ok_('checked' not in attrs)

        data = {}
        # let's enter 8 hours on the Monday
        data['d-20180101'] = str(settings.WORK_DAY)
        # 0 on the tuesday
        data['d-20180102'] = str(0)
        # and a half day on Wednesday
        data['d-20180103'] = str(settings.WORK_DAY / 2)

        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        entry = Entry.objects.get(pk=entry.pk)
        eq_(entry.total_hours, settings.WORK_DAY + settings.WORK_DAY / 2)

        eq_(Hours.objects.all().count(), 3)
        hour1 = Hours.objects.get(date=monday, entry=entry)
        eq_(hour1.hours, settings.WORK_DAY)
        hour2 = Hours.objects.get(date=tuesday, entry=entry)
        eq_(hour2.hours, 0)
        hour3 = Hours.objects.get(date=wednesday, entry=entry)
        eq_(hour3.hours, settings.WORK_DAY / 2)

        # expect it also to have sent a bunch of emails
        assert len(mail.outbox)
        email = mail.outbox[-1]
        #eq_(email.to, [peter.email])
        ok_(email.to)
        eq_(email.from_email, peter.email)
        ok_(peter.first_name in email.subject)
        ok_(peter.last_name in email.subject)
        ok_(peter.first_name in email.body)
        ok_(peter.last_name in email.body)
        ok_(entry.details in email.body)
        ok_(entry.start.strftime(settings.DEFAULT_DATE_FORMAT)
            in email.body)

        eq_(email.cc, [peter.email])
        ok_('--\n%s' % settings.EMAIL_SIGNATURE in email.body)
        eq_(len(email.attachments), 1)
        filename, content, mimetype = email.attachments[0]
        eq_(filename, 'event.ics')
        eq_(mimetype, 'text/calendar')
        ok_('Peter Bengtsson on PTO' in content)
        ok_('3 days' in content)

    def test_overlap_dates_errors(self):
        return  # Obsolete now

        monday = datetime.date(2011, 7, 25)
        tuesday = monday + datetime.timedelta(days=1)
        wednesday = monday + datetime.timedelta(days=2)
        thursday = monday + datetime.timedelta(days=3)
        friday = monday + datetime.timedelta(days=4)

        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )

        entry = Entry.objects.create(
          user=peter,
          start=monday,
          end=tuesday,
          total_hours=16,
        )
        Hours.objects.create(
          entry=entry,
          date=monday,
          hours=8,
        )
        Hours.objects.create(
          entry=entry,
          date=tuesday,
          hours=8,
        )

        entry2 = Entry.objects.create(
          user=peter,
          start=friday,
          end=friday,
          total_hours=8,
        )
        Hours.objects.create(
          entry=entry2,
          date=friday,
          hours=8,
        )

        url = reverse('dates.notify')
        peter.set_password('secret')
        peter.save()
        assert self.client.login(username='peter', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # make it start BEFORE monday and end on the monday
        response = self.client.post(url, {
          'start': monday - datetime.timedelta(days=3),
          'end': monday,
          'details': 'Going on a cruise',
        })
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)
        ok_('overlaps' in response.content)

        response = self.client.post(url, {
          'start': thursday,
          'end': friday,
          'details': 'Going on a cruise',
        })
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)
        ok_('overlaps' in response.content)

        response = self.client.post(url, {
          'start': tuesday,
          'end': wednesday,
          'details': 'Going on a cruise',
        })
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)
        ok_('overlaps' in response.content)

        response = self.client.post(url, {
          'start': friday,
          'end': friday,
          'details': 'Going on a cruise',
        })
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)
        ok_('overlaps' in response.content)

        response = self.client.post(url, {
          'start': friday,
          'end': friday + datetime.timedelta(days=7),
          'details': 'Going on a cruise',
        })
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)
        ok_('overlaps' in response.content)

        assert Entry.objects.all().count() == 2
        # add an entry with total_hours=None
        Entry.objects.create(
          user=peter,
          start=thursday,
          end=thursday,
          total_hours=None
        )
        assert Entry.objects.all().count() == 3

        response = self.client.post(url, {
          'start': wednesday,
          'end': thursday,
          'details': 'Going on a cruise',
        })
        eq_(response.status_code, 302)

        # added one and deleted one
        assert Entry.objects.all().count() == 3

    def _get_inputs(self, html, multiple=False, **filters):
        _input_regex = re.compile('<input (.*?)>', re.M | re.DOTALL)
        _attrs_regex = re.compile('(\w+)="([^"]+)"')
        if multiple:
            all_attrs = defaultdict(list)
        else:
            all_attrs = {}
        for input in _input_regex.findall(html):
            attrs = dict(_attrs_regex.findall(input))
            name = attrs.get('name', attrs.get('id', ''))
            for k, v in filters.items():
                if attrs.get(k, None) != v:
                    name = None
                    break
            if name:
                if multiple:
                    all_attrs[name].append(attrs)
                else:
                    all_attrs[name] = attrs
        return all_attrs

    def test_forbidden_access(self):
        bob = User.objects.create(
          username='bob',
        )
        today = datetime.date.today()
        entry = Entry.objects.create(
          user=bob,
          total_hours=8,
          start=today,
          end=today
        )

        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        peter.set_password('secret')
        peter.save()
        assert self.client.login(username='peter', password='secret')
        url1 = reverse('dates.hours', args=[entry.pk])
        response = self.client.get(url1)
        eq_(response.status_code, 403) # forbidden

        url2 = reverse('dates.emails_sent', args=[entry.pk])
        response = self.client.get(url2)
        eq_(response.status_code, 403) # forbidden

        peter.is_staff = True
        peter.save()

        response = self.client.get(url1)
        eq_(response.status_code, 200)
        response = self.client.get(url2)
        eq_(response.status_code, 200)

    def test_adding_hours_with_zeros_on_start(self):
        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        peter.set_password('secret')
        peter.save()
        assert self.client.login(username=peter.email, password='secret')

        monday = datetime.date(2011, 7, 25)
        assert monday.strftime('%A') == 'Monday'
        friday = monday + datetime.timedelta(days=4)
        assert friday.strftime('%A') == 'Friday'
        entry = Entry.objects.create(
          user=peter,
          start=monday,
          end=friday,
        )

        hours_url = reverse('dates.hours', args=[entry.pk])
        response = self.client.get(hours_url)
        eq_(response.status_code, 200)

        tuesday = monday + datetime.timedelta(days=1)
        wednesday = monday + datetime.timedelta(days=2)
        thursday = monday + datetime.timedelta(days=3)
        def date_to_name(d):
            return d.strftime('d-%Y%m%d')
        data = {
          date_to_name(monday): '0',
          date_to_name(tuesday): '4',
          date_to_name(wednesday): '8',
          date_to_name(thursday): '4',
          date_to_name(friday): '0',
        }
        response = self.client.post(hours_url, data)
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)

        data = {
          date_to_name(monday): '8',
          date_to_name(tuesday): '4',
          date_to_name(wednesday): '4',
          date_to_name(thursday): '0',
          date_to_name(friday): '0',
        }
        response = self.client.post(hours_url, data)
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)

    def test_calendar_events(self):
        url = reverse('dates.calendar_events')
        response = self.client.get(url)
        eq_(response.status_code, 403)

        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        peter.set_password('secret')
        peter.save()
        assert self.client.login(username=peter.email, password='secret')

        response = self.client.get(url)
        eq_(response.status_code, 400)
        _start = datetime.datetime(2011, 7, 1)
        data = {'start': time.mktime(_start.timetuple())}
        response = self.client.get(url, data)
        eq_(response.status_code, 400)
        _end = datetime.datetime(2011, 8, 1) - datetime.timedelta(days=1)
        data['end'] = 'x' * 12
        response = self.client.get(url, data)
        eq_(response.status_code, 400)
        data['end'] = time.mktime(_end.timetuple())
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(struct, [])

        # add some entries
        entry1 = Entry.objects.create(
          user=peter,
          start=datetime.date(2011, 7, 2),
          end=datetime.date(2011, 7, 2),
          total_hours=8,
        )

        entry2 = Entry.objects.create(
          user=peter,
          start=datetime.date(2011, 6, 30),
          end=datetime.date(2011, 7, 1),
          total_hours=8 * 2,
        )

        entry3 = Entry.objects.create(
          user=peter,
          start=datetime.date(2011, 7, 31),
          end=datetime.date(2011, 8, 1),
          total_hours=8 * 2,
        )

        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 3)
        eq_(set([x['id'] for x in struct]),
            set([entry1.pk, entry2.pk, entry3.pk]))

        # add some that are outside the search range and should not be returned
        entry4 = Entry.objects.create(
          user=peter,
          start=datetime.date(2011, 6, 30),
          end=datetime.date(2011, 6, 30),
          total_hours=8,
        )

        entry5 = Entry.objects.create(
          user=peter,
          start=datetime.date(2011, 8, 1),
          end=datetime.date(2011, 8, 1),
          total_hours=8,
        )

        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 3)
        # unchanged
        eq_(set([x['id'] for x in struct]),
            set([entry1.pk, entry2.pk, entry3.pk]))

        # add a curve-ball that spans the whole range
        entry6 = Entry.objects.create(
          user=peter,
          start=datetime.date(2011, 6, 30),
          end=datetime.date(2011, 8, 1),
          total_hours=8 * 30,
        )

        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 4)
        # one more now
        eq_(set([x['id'] for x in struct]),
            set([entry1.pk, entry2.pk, entry3.pk, entry6.pk]))

    def test_calendar_event_title(self):
        url = reverse('dates.calendar_events')
        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        peter.set_password('secret')
        peter.save()
        assert self.client.login(username=peter.email, password='secret')

        entry = Entry.objects.create(
          user=peter,
          start=datetime.date(2011, 7, 14),
          end=datetime.date(2011, 7, 14),
          total_hours=4,
          details=''
        )

        _start = datetime.datetime(2011, 7, 1)
        _end = datetime.datetime(2011, 8, 1) - datetime.timedelta(days=1)
        data = {
          'start': time.mktime(_start.timetuple()),
          'end': time.mktime(_end.timetuple())
        }
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 1)
        eq_(struct[0]['title'], '4 hours')

        entry.end += datetime.timedelta(days=5)
        entry.total_hours += 8 * 5
        entry.save()

        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 1)
        eq_(struct[0]['title'], '6 days')

        umpa = User.objects.create(
          username='umpa',
          email='umpa@mozilla.com',
          first_name='Umpa',
          last_name='Lumpa',
        )
        entry.user = umpa
        entry.save()

        umpa_profile = umpa.get_profile()
        umpa_profile.manager = 'pbengtsson@mozilla.com'
        umpa_profile.save()

        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 1)
        eq_(struct[0]['title'], 'Umpa Lumpa - 6 days')

        umpa.first_name = ''
        umpa.last_name = ''
        umpa.save()

        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 1)
        eq_(struct[0]['title'], 'umpa - 6 days')

        entry.details = 'Short'
        entry.save()
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 1)
        eq_(struct[0]['title'], 'umpa - 6 days, Short')

        entry.details = "This time it's going to be a really long one to test"
        entry.save()
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 1)
        ok_(struct[0]['title'].startswith('umpa - 6 days, This time'))
        ok_(struct[0]['title'].endswith('...'))

        Hours.objects.create(
          entry=entry,
          date=entry.start,
          hours=8,
          birthday=True
        )
        response = self.client.get(url, data)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct), 1)
        ok_('birthday' in struct[0]['title'])

    def test_notify_free_input(self):
        url = reverse('dates.notify')
        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        peter.set_password('secret')
        peter.save()

        assert self.client.login(username='peter', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        monday = datetime.date(2018, 1, 1)  # I know this is a Monday
        wednesday = monday + datetime.timedelta(days=2)
        notify = """
        mail@email.com,
        foo@bar.com ;
        Peter B <ppp@bbb.com>,
        not valid@ test.com;
        Axel Test <axe l@e..com>
        """
        notify += ';%s' % settings.EMAIL_BLACKLIST[-1]
        response = self.client.post(url, {'start': monday,
                                          'end': wednesday,
                                          'details': "Having fun",
                                          'notify': notify.replace('\n','\t')
                                          })
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)

        notify = notify.replace(settings.EMAIL_BLACKLIST[-1], '')
        response = self.client.post(url, {'start': monday,
                                          'end': wednesday,
                                          'details': "Having fun",
                                          'notify': notify.replace('\n','\t')
                                          })
        eq_(response.status_code, 302)
        url = urlparse(response['location']).path
        response = self.client.get(url)
        eq_(response.status_code, 200)
        tuesday = monday + datetime.timedelta(days=1)
        data = {
          monday.strftime('d-%Y%m%d'): 8,
          tuesday.strftime('d-%Y%m%d'): 8,
          wednesday.strftime('d-%Y%m%d'): 8,
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        response = self.client.get(response['location'])
        ok_('ppp@bbb.com' in response.content)
        ok_('mail@email.com' in response.content)
        ok_('valid@ test.com' not in response.content)
        ok_('axe l@e..com' not in response.content)
        ok_(settings.HR_MANAGERS[0] in response.content)

    def test_notify_notification_attachment(self):
        url = reverse('dates.notify')
        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        peter.set_password('secret')
        peter.save()

        assert self.client.login(username='peter', password='secret')
        monday = datetime.date(2018, 1, 1)  # I know this is a Monday
        wednesday = monday + datetime.timedelta(days=2)

        entry = Entry.objects.create(
          start=monday,
          end=wednesday,
          user=peter,
        )
        tuesday = monday + datetime.timedelta(days=1)
        data = {
          monday.strftime('d-%Y%m%d'): 8,
          tuesday.strftime('d-%Y%m%d'): 8,
          wednesday.strftime('d-%Y%m%d'): 8,
        }
        url = reverse('dates.hours', args=[entry.pk])
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        assert len(mail.outbox)
        email = mail.outbox[-1]

        attachment = email.attachments[0]
        filename, content, mimetype = attachment
        eq_(filename, 'event.ics')
        eq_(mimetype, 'text/calendar')
        ok_('Peter Bengtsson on PTO (3 days)' in content)

    def test_notify_notification_attachment_on_birthday(self):
        url = reverse('dates.notify')
        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        peter.set_password('secret')
        peter.save()

        assert self.client.login(username='peter', password='secret')
        monday = datetime.date(2018, 1, 1)  # I know this is a Monday
        wednesday = monday + datetime.timedelta(days=2)

        entry = Entry.objects.create(
          start=monday,
          end=monday,
          user=peter,
        )
        data = {
          monday.strftime('d-%Y%m%d'): '-1',
        }
        url = reverse('dates.hours', args=[entry.pk])
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        hours, = Hours.objects.all()
        assert hours.birthday

        assert len(mail.outbox)
        email = mail.outbox[-1]

        attachment = email.attachments[0]
        filename, content, mimetype = attachment
        eq_(filename, 'event.ics')
        eq_(mimetype, 'text/calendar')
        ok_('Peter Bengtsson' in content)
        ok_('birthday' in content)

    def test_notify_notification_attachment_one_day(self):
        url = reverse('dates.notify')
        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
        )
        peter.set_password('secret')
        peter.save()

        assert self.client.login(username='peter', password='secret')
        monday = datetime.date(2018, 1, 1)  # I know this is a Monday

        entry = Entry.objects.create(
          start=monday,
          end=monday,
          user=peter,
        )
        tuesday = monday + datetime.timedelta(days=1)
        data = {
          monday.strftime('d-%Y%m%d'): 4,
        }
        url = reverse('dates.hours', args=[entry.pk])
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        assert len(mail.outbox)
        email = mail.outbox[-1]

        attachment = email.attachments[0]
        filename, content, mimetype = attachment
        eq_(filename, 'event.ics')
        eq_(mimetype, 'text/calendar')
        ok_('peter on PTO (4 hours)' in content)

    def test_get_minions(self):
        from dates.views import get_minions
        gary = User.objects.create_user(
          'gary', 'gary@mozilla.com'
        )

        todd = User.objects.create_user(
          'todd', 'todd@mozilla.com',
        )
        profile = todd.get_profile()
        profile.manager = gary.email
        profile.save()

        mike = User.objects.create_user(
          'mike', 'mike@mozilla.com',
        )
        profile = mike.get_profile()
        profile.manager = todd.email
        profile.save()

        laura = User.objects.create_user(
          'laura', 'laura@mozilla.com',
        )
        profile = laura.get_profile()
        profile.manager = mike.email
        profile.save()

        peter = User.objects.create_user(
          'peter', 'peter@mozilla.com',
        )
        profile = peter.get_profile()
        profile.manager = laura.email
        profile.save()

        users = get_minions(gary, max_depth=1)
        eq_(users, [todd])

        users = get_minions(gary, max_depth=2)
        eq_(users, [todd, mike])

        users = get_minions(gary, max_depth=3)
        eq_(users, [todd, mike, laura])

        users = get_minions(gary, max_depth=4)
        eq_(users, [todd, mike, laura, peter])

        users = get_minions(gary, max_depth=10)
        eq_(users, [todd, mike, laura, peter])

        # from todd's perspective
        users = get_minions(todd, max_depth=1)
        eq_(users, [mike])

        users = get_minions(todd, max_depth=2)
        eq_(users, [mike, laura])

        users = get_minions(todd, max_depth=3)
        eq_(users, [mike, laura, peter])

        users = get_minions(todd, max_depth=10)
        eq_(users, [mike, laura, peter])

        # from laura's perspective
        users = get_minions(laura, max_depth=1)
        eq_(users, [peter])

        users = get_minions(laura, max_depth=99)
        eq_(users, [peter])

    def test_enter_reversal_pto(self):
        monday = datetime.date(2011, 7, 25)
        tuesday = monday + datetime.timedelta(days=1)

        peter = User.objects.create(
          username='peter',
          email='pbengtsson@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )

        entry = Entry.objects.create(
          user=peter,
          start=monday,
          end=monday,
          total_hours=8,
        )
        Hours.objects.create(
          entry=entry,
          date=monday,
          hours=8,
        )

        # Suppose you now change your mind and want it to be 4 hours on Monday
        # instead
        url = reverse('dates.notify')
        peter.set_password('secret')
        peter.save()
        assert self.client.login(username='peter', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.post(url, {
          'start': monday,
          'end': monday,
          'details': 'Going on a cruise',
        })
        eq_(response.status_code, 302)

        assert Entry.objects.all().count() == 2
        assert Hours.objects.all().count() == 1
        second_entry = Entry.objects.get(details='Going on a cruise')
        assert second_entry.total_hours is None

        url = reverse('dates.hours', args=[second_entry.pk])
        response = self.client.get(url)
        eq_(response.status_code, 200)

        radio_inputs = self._get_inputs(response.content, type="radio", checked="checked")
        attrs = radio_inputs.values()[0]
        date_key = radio_inputs.keys()[0]
        eq_(attrs['value'], '8')

        assert date_key == monday.strftime('d-%Y%m%d')
        data = {
          date_key: 4,
        }

        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        eq_(Entry.objects.all().count(), 3)
        eq_(Entry.objects.filter(user=peter).count(), 3)
        eq_(Hours.objects.all().count(), 3)

        second_entry = Entry.objects.get(pk=second_entry.pk)
        eq_(second_entry.total_hours, 4)

        total = sum(x.total_hours for x in Entry.objects.all())
        eq_(total, 4)

        ok_(Entry.objects.filter(total_hours=8))
        ok_(Entry.objects.filter(total_hours=-8))
        ok_(Entry.objects.filter(total_hours=4))

        # whilst we're at it, check that negative hours are included in the
        # list_json
        url = reverse('dates.list_json')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(response['Content-Type'].startswith('application/json'))
        struct = json.loads(response.content)
        entries = struct['aaData']
        eq_(len(entries), 3)
        totals = [x[4] for x in entries]
        eq_(sum(totals), 8 + 4 - 8)

    def test_list_json(self):
        url = reverse('dates.list_json')

        # start with no filtering
        peter = User.objects.create(
          username='peter',
          email='peter@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        laura = User.objects.create(
          username='laura',
          email='laura@mozilla.com',
          first_name='Laura',
          last_name='van Der Thomson',
        )

        one_day = datetime.timedelta(days=1)
        monday = datetime.date(2018, 1, 1)  # I know this is a Monday
        tuesday = monday + one_day

        e0 = Entry.objects.create(
          user=peter,
          start=monday,
          end=monday,
          total_hours=None,
          details='E0 Details'
        )
        e1 = Entry.objects.create(
          user=peter,
          start=tuesday,
          end=tuesday,
          total_hours=8,
          details='E1 Details'
        )
        e2 = Entry.objects.create(
          user=laura,
          start=monday,
          end=tuesday,
          total_hours=8 + 4,
          details='E2 Details'
        )

        response = self.client.get(url)
        eq_(response.status_code, 302)

        peter.set_password('secret')
        peter.save()
        assert self.client.login(username='peter', password='secret')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(response['Content-Type'].startswith('application/json'))
        ok_(e0.details not in response.content)
        ok_(e1.details in response.content)
        ok_(e2.details in response.content)
        struct = json.loads(response.content)
        entries = struct['aaData']

        def parse_date(s):
            d = datetime.datetime.strptime(s, '%Y-%m-%d')
            return d.date()

        for entry in entries:
            email = entry[0]
            first_name = entry[1]
            last_name = entry[2]
            add_date = parse_date(entry[3])
            total_hours = entry[4]
            start_date = parse_date(entry[5])
            end_date = parse_date(entry[6])
            city = entry[7]
            country = entry[8]
            details = entry[9]
            #...
            if email == peter.email:
                user = peter
            elif email == laura.email:
                user = laura
            else:
                raise AssertionError("unknown email")
            eq_(first_name, user.first_name)
            eq_(last_name, user.last_name)
            eq_(add_date, datetime.date.today())
            ok_(total_hours in (8, 12))
            ok_(start_date in (monday, tuesday))
            eq_(end_date, tuesday)
            ok_(details in (e1.details, e2.details))

        # test profile stuff
        p = peter.get_profile()
        p.city = 'London'
        p.country = 'UK'
        p.save()

        p = laura.get_profile()
        p.city = 'Washington DC'
        p.country = 'USA'
        p.save()

        response = self.client.get(url)
        struct = json.loads(response.content)
        entries = struct['aaData']
        for entry in entries:
            city = entry[7]
            ok_(city in ('London', 'Washington DC'))

            country = entry[8]
            ok_(country in ('UK', 'USA'))

        filter = {'name': 'PeteR'}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' not in response.content)

        filter = {'name': 'bengtssON'}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' not in response.content)

        filter = {'name': peter.email.capitalize()}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' not in response.content)

        filter = {'name': 'FOO@bar.com'}
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' not in response.content)

        filter = {'name': 'thomson'}
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' in response.content)

        filter = {'name': 'VAN DER Thomson'}
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' in response.content)

        filter = {'name': 'Laura VAN DER Thomson'}
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' in response.content)

        filter = {'name': 'Peter bengtsson'}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' not in response.content)

        e2.add_date -= datetime.timedelta(days=7)
        e2.save()

        filter = {'date_filed_to': datetime.date.today()}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' in response.content)

        filter = {'date_filed_to': (datetime.date.today() -
                                    one_day)}
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' in response.content)

        filter = {'date_filed_to': (datetime.date.today() -
                                    one_day),
                  'date_filed_from': (datetime.date.today() -
                                    datetime.timedelta(days=3)),
                  }
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' not in response.content)

        filter = {'date_filed_from': datetime.date.today()}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' not in response.content)

        filter = {'date_filed_from': 'invalid junk'}
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' not in response.content)

        # remember, ...
        # Peter's event was tuesday only
        # Laura's event was monday till tuesday
        filter = {'date_from': tuesday}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' in response.content)

        filter = {'date_from': monday}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' in response.content)

        filter = {'date_from': tuesday + one_day}
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' not in response.content)

        filter = {'date_to': monday}
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' in response.content)

        filter = {'date_to': monday - one_day}
        response = self.client.get(url, filter)
        ok_('Peter' not in response.content)
        ok_('Laura' not in response.content)

        filter = {'date_to': tuesday}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' in response.content)

        filter = {'date_to': tuesday + one_day}
        response = self.client.get(url, filter)
        ok_('Peter' in response.content)
        ok_('Laura' in response.content)

    def test_list(self):
        url = reverse('dates.list')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        peter = User.objects.create(
          username='peter',
          email='peter@mozilla.com',
          first_name='Peter',
          last_name='Bengtsson',
        )
        peter.set_password('secret')
        peter.save()
        assert self.client.login(username='peter', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # now create some entries
        laura = User.objects.create(
          username='laura',
          email='laura@mozilla.com',
          first_name='Laura',
          last_name='van Der Thomson',
        )

        one_day = datetime.timedelta(days=1)
        monday = datetime.date(2018, 1, 1)  # I know this is a Monday
        tuesday = monday + one_day

        e0 = Entry.objects.create(
          user=peter,
          start=monday,
          end=monday,
          total_hours=None,
          details='E0 Details'
        )
        e1 = Entry.objects.create(
          user=peter,
          start=tuesday,
          end=tuesday,
          total_hours=8,
          details='E1 Details'
        )
        e2 = Entry.objects.create(
          user=laura,
          start=monday,
          end=tuesday,
          total_hours=8 + 4,
          details='E2 Details'
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_dashboard_on_pto_right_now(self):
        """On the dashboard we can expect to see who is on PTO right now.
        Expect that past and future entries don't appear.
        It should also say how many days they have left.
        """

        jill = User.objects.create_user(
          'jill', 'jill@mozilla.com', password='secret'
        )
        assert self.client.login(username='jill', password='secret')
        response = self.client.get('/')
        eq_(response.status_code, 200)

        bobby = User.objects.create_user(
          'bobby', 'bobby@mozilla.com',
        )
        freddy = User.objects.create_user(
          'freddy', 'freddy@mozilla.com',
        )
        dicky = User.objects.create_user(
          'dicky', 'dicky@mozilla.com',
        )
        harry = User.objects.create_user(
          'harry', 'harry@mozilla.com',
        )

        ok_('bobby' not in response.content)
        ok_('freddy' not in response.content)
        ok_('dicky' not in response.content)
        ok_('harry' not in response.content)

        today = datetime.date.today()

        Entry.objects.create(
          user=bobby,
          total_hours=16,
          start=today - datetime.timedelta(days=2),
          end=today - datetime.timedelta(days=1),
        )
        response = self.client.get('/')
        ok_('bobby' not in response.content)

        Entry.objects.create(
          user=freddy,
          total_hours=16,
          start=today - datetime.timedelta(days=1),
          end=today,
        )
        response = self.client.get('/')
        ok_('freddy' in response.content)

        Entry.objects.create(
          user=dicky,
          total_hours=4,
          start=today,
          end=today,
        )
        response = self.client.get('/')
        ok_('dicky' in response.content)

        entry = Entry.objects.create(
          user=harry,
          total_hours=16,
          start=today + datetime.timedelta(days=1),
          end=today + datetime.timedelta(days=2),
        )
        response = self.client.get('/')
        ok_('harry' not in response.content)

        entry.start -= datetime.timedelta(days=1)
        entry.end -= datetime.timedelta(days=1)
        entry.save()
        response = self.client.get('/')
        ok_('harry' in response.content)
