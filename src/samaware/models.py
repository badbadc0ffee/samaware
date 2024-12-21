from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_scopes import ScopedManager
from pretalx.common.text.phrases import phrases
from pretalx.event.models import Event
from pretalx.person.models import User
from pretalx.schedule.models import TalkSlot
from pretalx.submission.models import Submission


class TechRider(models.Model):
    """
    Special technical requirements for a talk.

    Designed to be sync-able to ticket/task management systems.
    """

    event = models.ForeignKey(Event, related_name='tech_riders', on_delete=models.CASCADE)
    submission = models.OneToOneField(Submission, verbose_name=_('Submission'), related_name='tech_rider',
                                      on_delete=models.CASCADE)
    text = models.TextField(_('Text'), blank=True, help_text=phrases.base.use_markdown)
    author = models.ForeignKey(User, verbose_name=_('Author'), null=True,
                               related_name='authored_tech_riders', on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = ScopedManager(event='event')

    def __str__(self):
        # pylint: disable=E1101
        return f'TechRider(event={self.event.slug}, submission={self.submission})'

    def get_absolute_url(self):
        # pylint: disable=E1101
        return reverse('plugins:samaware:tech_rider_update', kwargs={'event': self.event.slug,
                                                                     'pk': self.pk})

    @classmethod
    def upcoming_objects(cls, event, timeframe):
        now = timezone.now()
        upcoming_threshold = now + timeframe

        slots = TalkSlot.objects.filter(start__gt=now, start__lt=upcoming_threshold, schedule__event=event)
        submissions = slots.values_list('submission', flat=True)

        return cls.objects.filter(submission__in=submissions, submission__event=event)


class SpeakerCareMessage(models.Model):
    """
    Organizers' internal information on a speaker.

    Will be displayed prominently when accessing the speaker or their talks. Think something like: "When this
    person shows up, they need to contact XXX as soon as possbible!"

    Unlike Internal Notes, this:
      - Is bound to a speaker, not a Submission.
      - Is supposed to be shown "in your face".
    """

    event = models.ForeignKey(Event, related_name='speaker_care_messages', on_delete=models.CASCADE)
    speaker = models.ForeignKey(User, verbose_name=_('Speaker'), related_name='speaker_care_messages',
                                on_delete=models.CASCADE)
    text = models.TextField(_('Text'))
    author = models.ForeignKey(User, verbose_name=_('Author'), null=True,
                               related_name='authored_care_messages', on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = ScopedManager(event='event')

    def __str__(self):
        # pylint: disable=E1101
        speaker_name = self.speaker.get_display_name()
        return f'SpeakerCareMessage(event={self.event.slug}, user={speaker_name})'

    def get_absolute_url(self):
        # pylint: disable=E1101
        return reverse('plugins:samaware:care_message_update', kwargs={'event': self.event.slug,
                                                                       'pk': self.pk})
