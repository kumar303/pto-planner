import datetime
from django.db import models
from django.contrib.auth.models import User


class Entry(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    total_hours = models.IntegerField(null=True, blank=True)
    start = models.DateField()
    end = models.DateField()
    details = models.TextField(blank=True)

    add_date = models.DateTimeField(default=datetime.datetime.utcnow)
    modify_date = models.DateTimeField(default=datetime.datetime.utcnow,
                                       auto_now=True)

    def __repr__(self):  # pragma: no cover
        return '<Entry: %s, %s - %s>' % (self.user,
                                         self.start,
                                         self.end)

class Hours(models.Model):
    entry = models.ForeignKey(Entry)
    hours = models.IntegerField()
    date = models.DateField()
    birthday = models.BooleanField(default=False)
