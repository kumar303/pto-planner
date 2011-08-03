import datetime
from optparse import make_option

from django.utils import simplejson as json
from django.core.management.base import NoArgsCommand
from django.contrib.auth.models import User
from django.db import transaction
from legacy.models import Pto
from dates.models import Entry, Hours
from dates.utils import parse_datetime, get_weekday_dates

class Command(NoArgsCommand):
    help = """
    Moves all old existing PTOs logged from the old app into this new app.
    """

    option_list = NoArgsCommand.option_list + (
                        make_option('--dryrun', default=False, action='store_true',
                                   help="Dry run, no database writes (Optional)"),
                        make_option('--all', action='store',
                                   help="All or nothing, rollback on any errors (Optional)"),
                        make_option('--encoding', action='store',
                                    help="Optional. If omitted will be utf8"),
    )


    def handle_noargs(self, **options):
        transaction_method = 'none'
        #transaction_method = options.get('all') and 'commit' or transaction_method
        transaction_method = options.get('dryrun') and 'rollback' or transaction_method
        max_count = options.get('all') and Pto.objects.all().count() or 1000

        _users = {}
        def get_user(email):
            if email not in _users:
                try:
                    user = User.objects.get(email=email)
                except User.DoesNotExist:
                    user = User.objects.create(
                      username=email.split('@')[0],
                      email=email,
                    )
                    user.set_unusable_password()
                _users[email] = user
            return _users[email]
        if not transaction_method == 'none':
            transaction.enter_transaction_management()
            transaction.managed(True)

        if max_count < Pto.objects.all().count():
            print "Capped to the first", max_count, "objects"

        count = 0
        for pto in Pto.objects.all().order_by('id')[:max_count]:
            #print pto.id
            user = get_user(pto.person)
            #print 'person', repr(pto.person), repr(user)
            added = self._timestamp_to_date(pto.added)
            #print 'added', repr(pto.added), added
            hours = pto.hours
            #print 'hours', float(pto.hours)

            #print 'details', repr(pto.details)
            start = self._timestamp_to_date(pto.start)
            #print 'start', repr(pto.start), start
            end = self._timestamp_to_date(pto.end)
            #print 'hours_daily', repr(pto.hours_daily)
            if pto.hours_daily:
                hours_daily = json.loads(pto.hours_daily)
                ts_keys = hours_daily.keys()
                for ts in ts_keys:
                    value = hours_daily.pop(ts)
                    hours_daily[self._timestamp_to_date(ts)] = value
                assert sum(hours_daily.values()) == hours
            else:
                try:
                    hours_daily = self._create_hours(hours, start, end)
                except ZeroDivisionError:
                    self._report_broken(pto)
                    continue
            #print hours, hours_daily
            # go ahead and add it
            entry = Entry.objects.create(
              user=user,
              start=start,
              end=end,
              total_hours=hours,
              details=pto.details.strip(),
              add_date=added,
              modify_date=added,
            )

            for d, t in hours_daily.items():
                Hours.objects.create(
                  entry=entry,
                  hours=t,
                  date=d,
                )

            pto.delete()
            count += 1

            #print 'end', repr(pto.end), end
            #print ""

        if not transaction_method == 'none':
            if transaction_method == 'rollback':
                print "rollbacked, no changed applied"
                transaction.rollback()
            else:
                transaction.commit()
                print "Migrated", count, "PTO entries"

    def _create_hours(self, total, start, end):
        r = {}
        #print ((total / 8), (end - start).days)
        if total / 8 == (end - start).days:
            # easy
            d = start
            while d < end:
                r[d] = 8
                d += datetime.timedelta(days=1)
        else:
            # this is only going to work if the total is a multiple of 4
            if int(total) % 4:
                return r
            total = int(total)
            #print range(total / 4)

            #print "total", total
            #print "start", start
            #print "end", end
            # spread em'
            dates = list(get_weekday_dates(start, end))
            for d in dates:
                r[d] = 0

            i = 0
            while total > 0:
                d = dates[i % len(dates)]
                r[d] += 4
                total -= 4
                i += 1
            print r
            #raise NotImplementedError

        return r

    def _timestamp_to_date(self, ts):
        if isinstance(ts, (int, long)):
            dt = datetime.datetime.fromtimestamp(ts)
        else:
            dt = parse_datetime(ts)
        return datetime.date(dt.year, dt.month, dt.day)

    def _report_broken(self, pto):
        print "*** BROKEN PTO ***"
        print "ID", pto.id
        print "Person:", pto.person,
        print "Added:", self._timestamp_to_date(pto.added)
        print "Hours:", pto.hours
        print "Start:", self._timestamp_to_date(pto.start)
        print "End:", self._timestamp_to_date(pto.end)
