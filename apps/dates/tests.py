import re
import time
from urlparse import urlparse
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

    def test_overlap_dates_errors(self):
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

    def _get_inputs(self, html, **filters):
        _input_regex = re.compile('<input (.*?)>', re.M | re.DOTALL)
        _attrs_regex = re.compile('(\w+)="([^"]+)"')
        all_attrs = {}
        for input in _input_regex.findall(html):
            attrs = dict(_attrs_regex.findall(input))
            name = attrs.get('name', attrs.get('id', ''))
            for k, v in filters.items():
                if attrs.get(k, None) != v:
                    name = None
                    break
            if name:
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
        #print response.content

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
        #print response.content
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
        print response.content
        eq_(response.status_code, 302)

        assert len(mail.outbox)
        email = mail.outbox[-1]

        attachment = email.attachments[0]
        filename, content, mimetype = attachment
        eq_(filename, 'event.ics')
        eq_(mimetype, 'text/calendar')
        ok_('Peter Bengtsson on PTO (2 days)' in content)

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
        print response.content
        eq_(response.status_code, 302)

        assert len(mail.outbox)
        email = mail.outbox[-1]

        attachment = email.attachments[0]
        filename, content, mimetype = attachment
        eq_(filename, 'event.ics')
        eq_(mimetype, 'text/calendar')
        ok_('peter on PTO (4 hours)' in content)
