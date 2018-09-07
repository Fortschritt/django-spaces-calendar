from django.conf.urls import url
from spaces.urls import space_patterns

from . import views

app_name = 'spaces_calendar'
urlpatterns = space_patterns(

    url(r'^calendar/$', views.index, name='index'),

    url(
        r'^calendar/(?P<year>\d{4})/$', 
        views.year_view, 
        name='yearly_view'
    ),

    url(r'^calendar/(\d{4})/(0?[1-9]|1[012])/$', 
        views.month_view, 
        name='monthly_view'
    ),

    url(r'^calendar/(\d{4})/Q([1-4])/$', 
        views.quarterly_view, 
        name='quarterly_view'
    ),

    url(
        r'^calendar/(\d{4})/(0?[1-9]|1[012])/([0-3]?\d)/$', 
        views.day_view, 
        name='daily_view'
    ),

    url(
        r'^calendar/events/add/$', 
        views.add_event, 
        name='add_event'
    ),

    url(
        r'^calendar/events/(\d+)/(\d+)/$', 
        views.occurrence_view, 
        name='occurrence'
    ),

    url(
        r'^calendar/events/(\d+)/$', 
        views.event_view, 
        name='event'
    ),

    url(
        r'^calendar/events/delete/(?P<pk>\d+)/$', 
        views.DeleteEvent.as_view(), 
        name='delete_event'
    ),
)