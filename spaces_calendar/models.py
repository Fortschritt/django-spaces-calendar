from django.conf import settings
from django.db import models
from spaces.models import Space,SpacePluginRegistry, SpacePlugin, SpaceModel
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from swingtime.models import Event


class SpacesCalendar(SpacePlugin):
    """
    Calender model for Spaces. This only provides general metadata.
    Actual events are CalendarEvent instances and have a ForeignKey to this
    model.
    """
    # active field (boolean) inherited from SpacePlugin
    # space field (foreignkey) inherited from SpacePlugin
    reverse_url = 'spaces_calendar:index'


class CalendarEvent(SpaceModel):
    """
    A calender event. Acts as a bridge between a space and django_swingtime.
    """
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    calendar = models.ForeignKey(SpacesCalendar, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    spaceplugin_field_name = "calendar"

    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')

    def __str__(self):
        return self.event.title

    def get_absolute_url(self):
        return reverse('spaces_calendar:event', args=[str(self.event.id)])
    

class CalendarPlugin(SpacePluginRegistry):
    """
    Provide a calendar plugin for Spaces. This makes the CalendarPlugin class
    visible to the plugin system.
    """
    name = 'spaces_calendar'
    title = _('Calendar')
    plugin_model = SpacesCalendar
    searchable_fields = (CalendarEvent, ('event__title','event__description'))