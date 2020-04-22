from django.conf import settings
from django.utils.translation import ugettext_noop as _

def create_notice_types(sender, **kwargs):
    if "pinax.notifications" in settings.INSTALLED_APPS:
        from spaces_notifications.utils import register_notification
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
