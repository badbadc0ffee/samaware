from django import forms
from django.utils.translation import gettext_lazy as _
from pretalx.submission.models import Submission


class NoRecordingFilter(forms.Form):

    # Restore Django's default renderer, which gets overwritten globally by pretalx
    default_renderer = forms.renderers.DjangoTemplates

    upcoming = forms.BooleanField(label=_('Next 4 hours only'), label_suffix='', required=False)


class MissingSpeakerFilter(forms.Form):

    default_renderer = forms.renderers.DjangoTemplates

    upcoming = forms.BooleanField(label=_('Next 4 hours only'), label_suffix='', required=False)


class InternalNotesForm(forms.ModelForm):

    default_renderer = forms.renderers.DjangoTemplates

    class Meta:
        model = Submission
        fields = ['internal_notes']
