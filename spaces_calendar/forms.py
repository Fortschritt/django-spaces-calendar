from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _
from swingtime.forms import SplitDateTimeWidget
from swingtime.forms import EventForm as st_EventForm
from swingtime.models import Occurrence, Event, EventType, Note

class SingleOccurrenceForm(forms.ModelForm):
    '''
    A simple form for adding and updating single Occurrence attributes

    '''
    
    start_time = forms.DateTimeField(label=_("Beginning"))
    end_time = forms.DateTimeField(label=_("End"))

    def save(self, event):
        start_time = self.cleaned_data['start_time']
        end_time = self.cleaned_data['end_time']
        o = Occurrence.objects.filter(
            event=event,
        ).delete()
        print('save():',start_time.tzinfo, start_time, o)
        event.add_occurrences(
            start_time,
            end_time,
        )
        return event

    class Meta:
        model = Occurrence
        fields = "__all__"


class EventForm(st_EventForm):
    '''
    A simple form for adding and updating Event attributes.
    Main difference to swingtime EventForm:
    We are overwriting 'description' with a note field to 
    enable descriptions of arbitrary length.
    '''

    event_type = forms.ModelChoiceField(
        queryset = EventType.objects.all(),
        widget = forms.RadioSelect(attrs={'required':'required'})
    )
    description = forms.CharField(
        widget = forms.Textarea(attrs={
            'rows': 3
        }),
    )

    class Meta:
        model = Event
        fields = "__all__"
        labels = {
            'title': _('title')
        }

    def __init__(self, *args, **kwargs):
        # if we edit an existing entry we have to ensure that the full note description gets
        # used as the inital text in the description field, not the short 
        super(EventForm, self).__init__(*args, **kwargs)
        if 'description' in self.initial.keys():
            note = Note.objects.get(
                content_type = ContentType.objects.get_for_model(self.Meta.model),
                object_id = self.initial['id']
            )
            self.initial['description'] = note.note

    def clean_description(self):
        # make sure description has the same max_length as the model field while preserving the full text.
        # FIXME: don't use the hardcoded 100 but get the length directly from the model field.
        self.cleaned_data['note'] = self.cleaned_data['description']
        return self.cleaned_data['description'][:100]

    def save(self):
        event = super(EventForm, self).save()
        # save description as extra Note to circumvent 100 char limit on the 
        # description field
        Note.objects.filter(
            content_type = ContentType.objects.get_for_model(event),
            object_id = event.id
        ).delete()
        Note.objects.create(
            content_type = ContentType.objects.get_for_model(event),
            object_id = event.id,
             note = self.cleaned_data['note']
        )
        return event
