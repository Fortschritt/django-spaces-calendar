from django.apps import AppConfig
from django.db.models.signals import post_migrate
from collab.util import db_table_exists

from spaces_calendar.signals import create_notice_types

#TODO: Put into settings.py
EVENT_TYPES = (
    {'abbr':'kursleitung', 'label':'Kursleitungs-Termine'},
    {'abbr':'teilnehmende', 'label':'Teilnehmenden-Termine'},
    {'abbr':'politisches', 'label':'Politische Termine'},
    {'abbr':'anderes', 'label':'Anderes'}
)

def create_event_types(type_list = EVENT_TYPES):
    '''
    Stupid way of avoiding fixtures. Checks for table existance to allow
    for the initial "python manage.py migrate" command to work.
    '''
    from swingtime.models import EventType
    if db_table_exists('swingtime_eventtype'):
        for t in type_list:
            EventType.objects.get_or_create(abbr=t['abbr'], label=t['label'])



class SpacesCalendarConfig(AppConfig):
    name = 'spaces_calendar'
    def ready(self):
        create_event_types()
        # activate activity streams for CalendarEvent
        from actstream import registry
        from .models import CalendarEvent
        registry.register(CalendarEvent)
        # register a custom notification
        """
        from spaces_notifications.utils import register_notification
        from django.utils.translation import ugettext_noop as _
        register_notification(
            'spaces_calendar_event_create',
            _('A new event has been created.'),
            _('A new event has been created.')
        )
        register_notification(
            'spaces_calendar_event_modify',
            _('An event has been modified.'),
            _('An event has been modified.')
        )
        """
        post_migrate.connect(create_notice_types, sender=self)
