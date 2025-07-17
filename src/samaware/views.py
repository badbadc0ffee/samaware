import datetime

from csp.decorators import csp_update
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.template.defaultfilters import linebreaks_filter
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic import DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView
from django_context_decorator import context
from pretalx.common.templatetags.rich_text import rich_text as rich_text_filter
from pretalx.common.views import CreateOrUpdateView
from pretalx.common.views.mixins import (
    ActionConfirmMixin,
    EventPermissionRequired,
    PermissionRequired,
    Sortable,
)
from pretalx.submission.models.submission import Submission, SubmissionStates

import samaware

from . import forms, models, queries


# htmx requires 'unsafe-eval' for its "delay" Modifier
# We could probably do cool stuff with nonces (`htmx.config.inlineScriptNonce`), but that would require
# nonces to be globally enabled for script-src from the pretalx config
# Given that this is only 'unsafe-eval' (*not* 'unsafe-inline'), I can live with it for now
@method_decorator(csp_update({'script-src': ["'unsafe-eval'"]}), name='dispatch')
class Dashboard(EventPermissionRequired, TemplateView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    template_name = 'samaware/dashboard.html'
    timeframe = datetime.timedelta(hours=4)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        no_recording_slots = queries.get_slots_without_recording(self.request.event)

        data['total_speakers'] = queries.get_all_speakers(self.request.event)
        data['arrived_speakers'] = queries.get_arrived_speakers(self.request.event)
        data['slots_missing_speakers'] = queries.get_slots_missing_speakers(self.request.event,
                                                                            self.timeframe)
        data['unreleased_changes'] = self.request.event.wip_schedule.changes
        data['speaker_care_messages'] = self.request.event.speaker_care_messages.all()
        data['tech_riders'] = self.request.event.tech_riders.all()
        data['tech_riders_4h'] = models.TechRider.upcoming_objects(self.request.event, self.timeframe)
        data['no_recording_slots'] = no_recording_slots
        data['no_recording_no_rider_slots'] = no_recording_slots.filter(submission__tech_rider__isnull=True)
        data['no_recording_slots_4h'] = queries.get_slots_without_recording(self.request.event,
                                                                            self.timeframe)

        return data


class TalkOverview(PermissionRequired, DetailView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    slug_field = 'code'
    slug_url_kwarg = 'code'
    template_name = 'samaware/talk_overview.html'
    context_object_name = 'submission'

    def get_queryset(self):
        return Submission.objects.filter(event=self.request.event).select_related('event', 'track')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        obj = self.object

        data['submission_is_confirmed'] = obj.state == SubmissionStates.CONFIRMED
        data['submission_unreleased_changes'] = queries.get_unreleased_changes_for_submission(obj)
        # Get Submission's slots in the currrent WiP Schedule
        data['submission_wip_slots'] = obj.slots.filter(schedule__version__isnull=True)

        data['speaker_profiles'] = {user: user.event_profile(obj.event) for user in obj.speakers.all()}
        data['other_event_talks'] = {
            user: queries.get_talks_in_other_events(user, obj.event) for user in obj.speakers.all()
        }
        data['speaker_care_messages'] = self.request.event.speaker_care_messages.filter(
            speaker__in=obj.speakers.all()
        )

        return data


class MissingSpeakersList(EventPermissionRequired, Sortable, ListView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    sortable_fields = ('submission__track__name', 'submission__title', 'start', 'room')
    default_sort_field = 'start'
    template_name = 'samaware/missing_speakers_list.html'
    context_object_name = 'slots'
    upcoming_timeframe = datetime.timedelta(hours=4)

    def get_queryset(self):
        filter_form = self.filter_form()
        if filter_form.is_valid() and filter_form.cleaned_data.get('upcoming'):
            slots = queries.get_slots_missing_speakers(self.request.event,
                                                       timeframe=self.upcoming_timeframe)
        else:
            slots = queries.get_slots_missing_speakers(self.request.event)

        slots = self.sort_queryset(slots)
        return slots.select_related('submission', 'submission__track', 'submission__event', 'room') \
                    .prefetch_related('submission__speakers')

    @context
    def event_profiles(self):
        profiles = queries.get_all_speakers(self.request.event).select_related('user', 'event')
        return {profile.user: profile for profile in profiles}

    @context
    def filter_form(self):
        return forms.UpcomingFilter(self.request.GET)


class NoRecordingList(EventPermissionRequired, Sortable, ListView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    sortable_fields = ('submission__track__name', 'submission__title', 'start', 'room')
    default_sort_field = 'start'
    template_name = 'samaware/no_recording_list.html'
    context_object_name = 'slots'
    upcoming_timeframe = datetime.timedelta(hours=4)

    def get_queryset(self):
        filter_form = self.filter_form()

        if filter_form.is_valid() and filter_form.cleaned_data.get('upcoming'):
            slots = queries.get_slots_without_recording(self.request.event,
                                                        timeframe=self.upcoming_timeframe)
        else:
            slots = queries.get_slots_without_recording(self.request.event)

        if filter_form.is_valid() and filter_form.cleaned_data.get('no_rider'):
            slots = slots.filter(submission__tech_rider__isnull=True)

        slots = self.sort_queryset(slots)
        return slots.select_related('submission', 'submission__track', 'submission__event', 'room')

    @context
    def filter_form(self):
        return forms.NoRecordingFilter(self.request.GET)


class TechRiderList(EventPermissionRequired, Sortable, ListView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    sortable_fields = ('submission__title', 'start', 'room')
    default_sort_field = 'submission__title'
    template_name = 'samaware/tech_rider_list.html'
    context_object_name = 'slots'
    upcoming_timeframe = datetime.timedelta(hours=4)

    def get_queryset(self):
        slots = self.request.event.wip_schedule.talks.filter(submission__tech_rider__isnull=False)

        filter_form = self.filter_form()
        if filter_form.is_valid() and filter_form.cleaned_data.get('upcoming'):
            now = timezone.now()
            upcoming_threshold = now + self.upcoming_timeframe
            slots = slots.filter(start__gt=now, start__lt=upcoming_threshold)

        slots = self.sort_queryset(slots)
        return slots.select_related('submission', 'submission__tech_rider', 'submission__event', 'room')

    @context
    def filter_form(self):
        return forms.UpcomingFilter(self.request.GET)


class BaseTechRiderEdit(PermissionRequired, CreateOrUpdateView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    model = models.TechRider
    form_class = forms.TechRiderForm

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object = None

    def get_permission_object(self):
        obj = self.get_object()
        if obj:
            return obj.submission
        else:
            return self.request.event

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.event = self.request.event
        self.object.author = self.request.user

        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class TechRiderEdit(BaseTechRiderEdit):

    template_name = 'samaware/tech_rider_edit.html'

    def get_object(self, queryset=None):
        if self.object is not None:
            return self.object

        if queryset is None:
            queryset = self.get_queryset()

        if 'pk' in self.kwargs:
            return queryset.get(pk=self.kwargs['pk'], event=self.request.event)
        else:
            return None

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        submissions_filter = Q(state__in=SubmissionStates.accepted_states) | \
                             Q(pending_state__in=SubmissionStates.accepted_states)
        if self.object:
            submissions_filter |= Q(pk=self.object.submission.pk)
        kwargs['submission_queryset'] = self.request.event.submissions.filter(submissions_filter)

        return kwargs


class TechRiderDelete(PermissionRequired, ActionConfirmMixin, DeleteView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    model = models.TechRider

    def get_permission_object(self):
        return self.get_object().submission

    @property
    def action_object_name(self):
        return _('Tech Rider for:') + ' ' + self.get_object().submission.title

    @property
    def action_back_url(self):
        return self.get_object().get_absolute_url()

    @property
    def success_url(self):
        return reverse('plugins:samaware:tech_rider_list', kwargs={'event': self.get_object().event.slug})


class CareMessageList(EventPermissionRequired, ListView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    template_name = 'samaware/care_message_list.html'
    # "messages" is already used globally
    context_object_name = 'care_messages'

    def get_queryset(self):
        messages = models.SpeakerCareMessage.objects.filter(event=self.request.event)
        return messages.order_by('speaker__name').select_related('speaker')


class CareMessageEdit(PermissionRequired, CreateOrUpdateView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    model = models.SpeakerCareMessage
    form_class = forms.CareMessageForm
    template_name = 'samaware/care_message_edit.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object = None

    def get_object(self, _queryset=None):
        if self.object is not None:
            return self.object
        elif 'pk' in self.kwargs:
            return models.SpeakerCareMessage.objects.get(pk=self.kwargs['pk'], event=self.request.event)
        else:
            return None

    def get_permission_object(self):
        obj = self.get_object()
        if obj:
            return obj.speaker.event_profile(self.request.event)
        else:
            return self.request.event

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        speaker_queryset = self.request.event.speakers
        kwargs['speaker_queryset'] = speaker_queryset.order_by('name')

        if not self.get_object() and 'speaker' in self.request.GET:
            speaker = speaker_queryset.filter(code=self.request.GET['speaker']).first()
            if speaker:
                kwargs['speaker_initial'] = speaker

        return kwargs

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.event = self.request.event
        self.object.author = self.request.user

        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class CareMessageDelete(PermissionRequired, ActionConfirmMixin, DeleteView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    model = models.SpeakerCareMessage

    def get_permission_object(self):
        return self.get_object().speaker.event_profile(self.request.event)

    @property
    def action_object_name(self):
        return _('Speaker Care Message regarding:') + ' ' + self.get_object().speaker.get_display_name()

    @property
    def action_back_url(self):
        return self.get_object().get_absolute_url()

    @property
    def success_url(self):
        return reverse('plugins:samaware:care_message_list', kwargs={'event': self.get_object().event.slug})


class SamAwareSettings(EventPermissionRequired, FormView):

    permission_required = 'orga.change_settings'
    form_class = forms.SamAwareSettingsForm
    template_name = 'samaware/settings.html'

    def get_success_url(self):
        return self.request.path

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['event'] = self.request.event
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


class SearchFragment(EventPermissionRequired, TemplateView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    template_name = 'samaware/fragments/search_result.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        slots = self.request.event.wip_schedule.talks.filter(submission__isnull=False)
        speakers = queries.get_all_speakers(self.request.event).select_related('user')

        query = self.request.GET.get('query')
        if query:
            users = speakers.filter(user__name__icontains=query).values_list('user', flat=True)
            slots = slots.filter(Q(submission__title__icontains=query) | Q(submission__speakers__in=users))

        data['slots'] = slots.order_by('submission__title').distinct() \
                             .select_related('submission', 'submission__track', 'submission__event', 'room')
        data['event_profiles'] = {profile.user: profile for profile in speakers}

        return data


class InternalNotesFragment(PermissionRequired, UpdateView):

    permission_required = samaware.REQUIRED_PERMISSIONS
    model = Submission
    slug_field = 'code'
    slug_url_kwarg = 'code'
    form_class = forms.InternalNotesForm
    template_name = 'samaware/fragments/form_or_content.html'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        data['headline'] = _('Internal Notes')
        data['show_form'] = True
        data['fragment_target'] = self.request.path

        return data

    def form_valid(self, form):
        self.object = form.save()  # pylint: disable=W0201

        data = self.get_context_data()
        data['show_form'] = False
        data['content'] = linebreaks_filter(self.object.internal_notes)

        return self.render_to_response(data)


class TechRiderFragment(BaseTechRiderEdit):

    slug_url_kwarg = 'code'
    template_name = 'samaware/fragments/form_or_content.html'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.object = None
        self.submission = None

    def get_object(self, queryset=None):
        if self.object is not None:
            return self.object

        if queryset is None:
            queryset = self.get_queryset()

        self.submission = Submission.objects.get(code=self.kwargs[self.slug_url_kwarg],
                                                 event=self.request.event)
        return queryset.filter(submission=self.submission, event=self.request.event).first()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        data['headline'] = _('Tech Rider')
        data['show_form'] = True
        data['fragment_target'] = self.request.path

        return data

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs['submission_initial'] = self.submission
        kwargs['submission_queryset'] = Submission.objects.filter(pk=self.submission.pk)
        kwargs['hide_submission_field'] = True

        return kwargs

    def form_valid(self, form):
        super().form_valid(form)

        data = self.get_context_data()
        data['show_form'] = False
        data['content'] = rich_text_filter(self.object.text)

        return self.render_to_response(data)
