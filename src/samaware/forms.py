from django import forms
from django.utils.translation import gettext_lazy as _
from django_scopes.forms import SafeModelChoiceField
from pretalx.common.forms.widgets import EnhancedSelect
from pretalx.submission.models import Submission

from .models import SamAwareSettings, SpeakerCareMessage, TechRider


class SubmissionChoiceField(SafeModelChoiceField):

    def label_from_instance(self, obj):
        return obj.title


class UpcomingFilter(forms.Form):

    # Restore Django's default renderer, which gets overwritten globally by pretalx
    default_renderer = forms.renderers.DjangoTemplates

    upcoming = forms.BooleanField(label=_('Next 4 hours only'), label_suffix='', required=False)


class NoRecordingFilter(UpcomingFilter):

    no_rider = forms.BooleanField(label=_('Without Tech Rider only'), label_suffix='', required=False)


class InternalNotesForm(forms.ModelForm):

    default_renderer = forms.renderers.DjangoTemplates

    class Meta:
        model = Submission
        fields = ['internal_notes']


class TechRiderForm(forms.ModelForm):

    class Meta:
        model = TechRider
        fields = ['submission', 'text']
        field_classes = {
            'submission': SubmissionChoiceField,
        }
        widgets = {'submission': EnhancedSelect()}

    def __init__(self, *args, **kwargs):
        submission_queryset = kwargs.pop('submission_queryset')
        submission_initial = kwargs.pop('submission_initial', None)
        hide_submission_field = kwargs.pop('hide_submission_field', False)

        super().__init__(*args, **kwargs)

        self.fields['submission'].queryset = submission_queryset
        if submission_initial:
            self.fields['submission'].initial = submission_initial
        if hide_submission_field:
            self.fields['submission'].widget = self.fields['submission'].hidden_widget()


class CareMessageForm(forms.ModelForm):

    class Meta:
        model = SpeakerCareMessage
        fields = ['speaker', 'text']
        widgets = {'speaker': EnhancedSelect()}

    def __init__(self, *args, **kwargs):
        speaker_queryset = kwargs.pop('speaker_queryset')
        speaker_initial = kwargs.pop('speaker_initial', None)

        super().__init__(*args, **kwargs)

        self.fields['speaker'].queryset = speaker_queryset
        if speaker_initial:
            self.fields['speaker'].initial = speaker_initial


class SamAwareSettingsForm(forms.ModelForm):

    class Meta:
        model = SamAwareSettings
        fields = ['wekan_base_url', 'wekan_username', 'wekan_password', 'wekan_board_id', 'wekan_list_title',
                  'wekan_swimlane_title']
        widgets = {'wekan_password': forms.PasswordInput(render_value=True)}

    def __init__(self, *args, **kwargs):
        event = kwargs.pop('event')
        self.instance, _ = SamAwareSettings.objects.get_or_create(event=event)
        super().__init__(*args, **kwargs, instance=self.instance)
