from django.conf.urls.defaults import patterns, url
import views

urlpatterns = patterns('',
    url(r'^$', views.home, name='dates.home'),
    url(r'^notify/$', views.notify, name='dates.notify'),
    url(r'^(?P<pk>\d+)/hours/$', views.hours, name='dates.hours'),
    url(r'^(?P<pk>\d+)/sent/$', views.emails_sent, name='dates.emails_sent'),
    url(r'^list/$', views.list_, name='dates.list'),
    url(r'^list.json$', views.list_json, name='dates.list_json'),
    url(r'^calendar/events/$', views.calendar_events, name='dates.calendar_events'),
    #url(r'^$', 'home', name='pto.home'),
    #url(r'^calculate_pto\.json$', 'calculate_pto', name='pto.calculate_pto'),
)
