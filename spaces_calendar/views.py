from datetime import datetime, date, timedelta
from dateutil import parser
import calendar
import itertools
from math import ceil
import pytz

from django import http
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.views.generic.edit import DeleteView

from actstream.signals import action as actstream_action
from swingtime.models import EventType, Event, Occurrence
from swingtime.views import add_event  as st_add_event
from swingtime.views import event_view  as st_event_view
from swingtime.views import occurrence_view  as st_occurrence_view
from swingtime.views import _datetime_view  as st_datetime_view
from swingtime.views import month_view as st_month_view
from swingtime.views import year_view as st_year_view
from swingtime import forms as st_forms

from collab.decorators import permission_required_or_403
from collab.util import is_owner_or_admin
from spaces.models import SpacePluginRegistry
from spaces_notifications.forms import NotificationFormSet
from spaces_notifications.mixins import process_n12n_formset
from .decorators import event_owner_or_admin_required
from .models import SpacesCalendar, CalendarEvent, CalendarPlugin
from . import forms

def base_context(context = {}):
    """
        Prefill the calendar context with common values
    """
    context['plugin_selected'] = CalendarPlugin.name
    context['plugin'] = CalendarPlugin
    return context

@permission_required_or_403('access_space')
def index(request):
    '''
    Default calendar view. Should be a simple forward.
    '''
    now = timezone.now()
    year = now.year
    quarter = int(ceil(now.month/3.))
    return quarterly_view(request, year, quarter)

@permission_required_or_403('access_space')
def add_event(
    request,
    template='spaces_calendar/add_event.html',
    event_form_class=forms.EventForm,
    recurrence_form_class=forms.SingleOccurrenceForm
):
    '''
    Add a new ``Event`` instance and 1 or more associated ``Occurrence``s.
    
    Context parameters:
    
    ``dtstart``
        a datetime.datetime object representing the GET request value if present,
        otherwise None
    
    ``event_form``
        a form object for updating the event
    ``recurrence_form``
        a form object for adding occurrences
    
    This function is mostly identical to the swingtime original, but additionally
    binds the new event to a Space instance.
    '''
    dtstart = None
    if request.method == 'POST':
        event_form = event_form_class(request.POST)
        recurrence_form = recurrence_form_class(request.POST)
        n12n_formset = NotificationFormSet(request.SPACE, request.POST)
        if event_form.is_valid() and recurrence_form.is_valid():
            event = event_form.save()
            cal = SpacesCalendar.objects.get(space=request.SPACE)
            recurrence_form.save(event)
            calendar_event = CalendarEvent.objects.create(
                event=event, 
                calendar=cal,
                author=request.user
            )
            actstream_action.send(
                sender=request.user, 
                verb=_("was created"),
                target=request.SPACE, 
                action_object=calendar_event
            )
            messages.success(request, _('Event saved successfully.'))
            process_n12n_formset(
                n12n_formset,
                'spaces_calendar_event_create',
                request.SPACE,
                calendar_event,
                calendar_event.get_absolute_url()
            )
            return redirect(calendar_event.get_absolute_url())
    else:
        if 'dtstart' in request.GET:
            try:
                dtstart = parser.parse(request.GET['dtstart'])
                if timezone.is_naive(dtstart):
                    dtstart = pytz.timezone(settings.TIME_ZONE).localize(dtstart)
            except(TypeError, ValueError) as exc:
                # TODO: A badly formatted date is passed to add_event
                logging.warning(exc)
        
        dtstart = dtstart or timezone.now()
        event_form = event_form_class()
        recurrence_form = recurrence_form_class(initial={'dtstart': dtstart})
        n12n_formset = NotificationFormSet(request.SPACE)
            
    return render(
        request,
        template,
        {
            'dtstart': dtstart, 
            'event_form': event_form, 
            'recurrence_form': recurrence_form,
            'notification_formset': n12n_formset
        }
    )

@permission_required_or_403('access_space')
def event_view(
    request,
    pk,
    template='spaces_calendar/event_detail.html',
    event_form_class=forms.EventForm,
    recurrence_form_class=forms.SingleOccurrenceForm
):
    '''
    View an ``Event`` instance and optionally update either the event or its
    occurrences.
    Context parameters:
    ``event``
        the event keyed by ``pk``
        
    ``event_form``
        a form object for updating the event
        
    ``recurrence_form``
        a form object for adding occurrences

    This is mostly identical to the swingtime original. We just added activity streams on
    instance creation/updates.
    '''
    event = get_object_or_404(Event, pk=pk)
    time_format = '%Y-%m-%d %H:%M'
    # why do I have to do astimezone()? In other places django sorts it out by itself...
    tzinfo = timezone.get_current_timezone()
    start_time  = event.occurrence_set.first().start_time.astimezone(tzinfo).strftime(time_format)
    end_time    = event.occurrence_set.first().end_time.astimezone(tzinfo).strftime(time_format)
    if request.method == 'POST':
        if not is_owner_or_admin(request.user, event.calendarevent.author, request.SPACE):
            raise PermissionDenied
        event_form = event_form_class(request.POST, instance=event)
        recurrence_form = recurrence_form_class(request.POST, initial={'start_time':start_time, 'end_time':end_time})
        n12n_formset = NotificationFormSet(request.SPACE, request.POST)
        if event_form.is_valid():
            event = event_form.save()
            if recurrence_form.is_valid():
                recurrence_form.save(event)
            actstream_action.send(
                sender=request.user, 
                verb=_("was updated"), 
                target=request.SPACE, 
                action_object=event.calendarevent
            )
            messages.success(request, _('Event updated successfully.'))
            process_n12n_formset(
                n12n_formset,
                'spaces_calendar_event_modify',
                request.SPACE,
                event.calendarevent,
                event.calendarevent.get_absolute_url()
            )
            return http.HttpResponseRedirect(request.path)
    else:
        event_form = event_form_class(instance=event)
        recurrence_form = recurrence_form_class(initial={'start_time':start_time, 'end_time':end_time})
        n12n_formset = NotificationFormSet(request.SPACE)

    data = {
        'event': event,
        'event_form': event_form,
        'recurrence_form': recurrence_form,
        'notification_formset': n12n_formset
    }
    return render(request, template, data)

@permission_required_or_403('access_space')
def occurrence_view(
    request,
    event_pk,
    pk,
    template='swingtime/occurrence_detail.html',
    form_class=st_forms.SingleOccurrenceForm
):  
    '''
    This view just forwards to swingtime.views.occurence_view.
    '''
    return st_occurrence_view(request, event_pk, pk, template, form_class)

@permission_required_or_403('access_space')
def day_view(
    request, 
    year, 
    month, 
    day, 
    template='swingtime/daily_view.html', 
    **params
):
    ''' 
    This view justforwards to swingtime.views._datetime_view.
    '''
    dt = datetime(int(year), int(month), int(day), tzinfo=pytz.timezone(settings.TIME_ZONE))
    return st_datetime_view(request, template, dt, **params)

def day_names_for_month(year, month):
    """
    Helper function providing a dict containing the names of all days
    for a given year and month.
    """
    tzinfo = timezone.get_current_timezone()
    week_list = calendar.monthcalendar(year, month)
    ret = {}
    for week in week_list:
        for day in week:
            if day > 0:
                day_name = datetime(year, month, day, tzinfo=tzinfo)\
                            .strftime('%a')
                ret[day] = _(day_name)
    return ret

def day_names_for_quarter(year, months):
    quarter = {}
    for month in months:
        quarter[month] = day_names_for_month(year, month)
    return quarter

def days_between_start_and_end(o, month):
    """
        for the given occurrence and the current month, return a list of days 
        between start day and end day that are part of the current month.
 
        Examplea: for a workshop starting at friday the 4. and ending at sunday
            the 6., the function would return [5], for the saturday in between.

    """
    days_between = []
    delta = o.end_time - o.start_time
    for n in range(1,delta.days+1):
        current_dt = o.start_time + timedelta(n)
        if  current_dt.month == month and current_dt.day != o.end_time.day:
            days_between.append(current_dt.day)
    return days_between
    


def occurrences_by_day_of_month(occurrences, start_day, end_day, month):
    """
        group occurrences by day of month.
    """ 
    # group all occurrences by day, create a dict with entries starting, ending
    # or running throughout that day.
    occurrences_starting_this_month = [o for o in occurrences if o.start_time.month == month]
    by_day = dict([(dt, {'starts':list(o)}) for dt,o in itertools.groupby(occurrences_starting_this_month, start_day)])
    throughout_the_day = {}
    # --> occurrences kommt hier schon leer an --> die aufrufende Funktion ist das Problem.
    for dt,o_list in itertools.groupby(occurrences, end_day):
        if dt not in by_day.keys():
            by_day[dt] = {}
        o_ends = []
        for o in o_list:
            days_between = days_between_start_and_end(o,month)
            for day in days_between:
                if day not in throughout_the_day.keys():
                    throughout_the_day[day] = []
                throughout_the_day[day].append(o)
            if o.end_time.month == month and o.start_time.day != o.end_time.day: # Note: this is potentially buggy in combination with DST and multiple timezones.
                o_ends.append(o)
        by_day[dt]['ends'] = o_ends
    for day in throughout_the_day.keys():
        if day not in by_day.keys():
            by_day[day] = {}
        by_day[day]['throughout'] = set(throughout_the_day[day])
    return by_day

@permission_required_or_403('access_space')
def month_view(
    request, 
    year, 
    month,
    template='spaces_calendar/monthly_view.html',
    queryset=None
):
    '''
    Adaptation of swingtimes monthly view for spaces. Adds Space awareness and
    full names for the days of the month.
    Original description:
    Render a tradional calendar grid view with temporal navigation variables.

    Context parameters:
    
    ``today``
        the current datetime.datetime value
        
    ``calendar``
        a list of rows containing (day, items) cells, where day is the day of
        the month integer and items is a (potentially empty) list of occurrence
        for the day
        
    ``this_month``
        a datetime.datetime representing the first day of the month
    
    ``next_month``
        this_month + 1 month
    
    ``last_month``
        this_month - 1 month
    
    '''
    year, month = int(year), int(month)
    cal         = calendar.monthcalendar(year, month)
    dtstart     = datetime(year, month, 1)
    last_day    = max(cal[-1])
    dtend       = datetime(year, month, last_day)


    if queryset == None:
        space_cal   = SpacesCalendar.objects.get(space=request.SPACE)
        queryset = Occurrence.objects\
                        .select_related()\
                        .filter(event__calendarevent__calendar = space_cal)
    else:
        queryset._clone()

    occurrences = queryset.filter(
        Q(start_time__year=year, start_time__month=month) |
        Q(end_time__year=year, end_time__month=month)
    )


    def start_day(o):
        return o.start_time.day

    def end_day(o):
        return o.end_time.day

    by_day = occurrences_by_day_of_month(occurrences, start_day, end_day, month)

    context = {
        'today':      timezone.now(),
        'calendar':   [[(d, by_day.get(d, [])) for d in row] for row in cal],
        'this_month': dtstart,
        'next_month': dtstart + timedelta(days=+last_day),
        'last_month': dtstart + timedelta(days=-1),
        'day_names':  day_names_for_month(year, month),
    }
    return render(request, template, context)

@permission_required_or_403('access_space')
def quarterly_view(
    request,
    year,
    quarter,
    template='spaces_calendar/quarterly_view.html',
    queryset=None
):
    """
    Like monthly view, but generates data (and displays it) for 3 months at 
    once.
    """
    year, quarter   = int(year), int(quarter)
    months          = [[1,2,3], [4,5,6], [7,8,9], [10,11,12]][quarter-1]
    cals            = [calendar.monthcalendar(year, month) for month in months]
    dtstart         = datetime(year, months[0], 1)
    last_day        = max(cals[-1][-1])
    dtend           = datetime(year, months[-1], last_day)


    # FIXME: queryset is the same as in monthly_view -> not DRY
    if queryset == None:
        space_cal   = SpacesCalendar.objects.get(space=request.SPACE)
        queryset = Occurrence.objects\
                        .select_related()\
                        .filter(event__calendarevent__calendar = space_cal)
    else:
        queryset._clone()

    occurrences = {}
    for month in months: # bug: this will not display events starting in the month before and ending in the month after. OTOH that's hardly an 'event' anymore...
        occurrences[month] = queryset.filter(
            Q(start_time__year=year, start_time__month=month) |
            Q(end_time__year=year, end_time__month=month)
        )

    def start_day(o):
        return o.start_time.day

    def end_day(o):
        return o.end_time.day

    by_day = {}
    for month in months:
        #by_day[month] = dict([(dt, list(o)) for dt,o in itertools.groupby(occurrences[month], start_day)])
        by_day[month] = occurrences_by_day_of_month(occurrences[month], start_day, end_day, month)

    calendars = []
    month_idx = 0
    for month in months:
        calendars.append([[(d, by_day[month].get(d, [])) for d in row] for row in cals[month_idx]])
        month_idx += 1

    this_quarter = {
        'quarter'   : quarter,
        'year'      : year,
    }
    next_quarter = {
        'quarter'   : [1,2,3,4][(quarter) % 4],
        'year'      : year if this_quarter['quarter'] < 4 else year+1,
    }
    last_quarter = {
        'quarter'   : [1,2,3,4][(quarter-2) % 4],
        'year'      : year if this_quarter['quarter'] > 1 else year-1,
    }

    context = {
        'today':        timezone.now(),
        'calendars':    calendars,
        'months':       months,
        'this_quarter': this_quarter,
        'next_quarter': next_quarter,
        'last_quarter': last_quarter,
        'quarterly_day_names':  day_names_for_quarter(year, months),
    }
    context = base_context(context)

    return render(request, template, context)

@permission_required_or_403('access_space')
def year_view(
    request,
    year,
    template='swingtime/yearly_view.html',
    queryset=None
):
    '''
    This view just forwards to swingtime.views.year_view.
    '''
    return st_year_view(request, year, month, template, queryset)

class DeleteEvent(DeleteView):

    model = Event
    success_message = _("Event was deleted successfully.")
    success_url = reverse_lazy('spaces_calendar:index')

    @event_owner_or_admin_required
    @method_decorator(permission_required_or_403('access_space'))
    def delete(self, request, *args, **kwargs):
        messages.success(request, self.success_message)
        return super(DeleteEvent, self).delete(request, *args, **kwargs)


    # ensure only events of own space can get deleted
    def get_queryset(self):
        qs = super(DeleteEvent, self).get_queryset()
        qs = qs.filter(calendarevent__calendar__space=self.request.SPACE)
        return qs
