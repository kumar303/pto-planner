from datetime import date, datetime, timedelta
from decimal import Decimal
import jingo

from django.core.urlresolvers import reverse

from dateutil.parser import parse as parse_datetime

from .decorators import json_view


def home(request):
    return jingo.render(request, 'pto/home.html',
                        dict(calculate_pto_url=reverse('pto.calculate_pto')))


@json_view
def calculate_pto(request):
    d = date.today()
    today = datetime(d.year, d.month, d.day, 0, 0, 0)
    trip_start = parse_datetime(request.GET['start_date'])
    pointer = today
    days_per_quarter = Decimal(request.GET['per_quarter'])
    days_avail = Decimal(request.GET['days_avail'])
    while pointer <= trip_start:
        if pointer.day == 1 or pointer.day == 15:
            days_avail += days_per_quarter
        if pointer.day > 15:
            add_days = days_til_1st(pointer)
        else:
            add_days = 15 - pointer.day
        if add_days == 0:
            add_days = 15  # 1st of the month
        pointer += timedelta(days=add_days)
    return dict(days_available_on_start=str(round(days_avail, 2)))


def days_til_1st(a_datetime):
    """Returns the number of days until the 1st of the next month."""
    next = a_datetime.replace(day=28)
    while next.month == a_datetime.month:
        next = next + timedelta(days=1)
    return (next - a_datetime).days
