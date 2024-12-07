from django import forms
from django.utils.translation import gettext_lazy as _


class NoRecordingFilter(forms.Form):

    # Restore Django's default renderer, which gets overwritten globally by pretalx
    default_renderer = forms.renderers.DjangoTemplates

    upcoming = forms.BooleanField(label=_('Next 4 hours only'), label_suffix='', required=False)
