import logging

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

from . import wekan

# pylint: disable=E1101


class SamAwareSettings(models.Model):

    event = models.OneToOneField(Event, related_name='samaware_settings', on_delete=models.CASCADE)
    wekan_base_url = models.URLField(
        verbose_name=_('Wekan Base URL'), blank=True, default='',
        help_text=_('Start page URL of the Wekan instance for Tech Rider sync.')
    )
    wekan_username = models.CharField(
        verbose_name=_('Wekan Username'), max_length=100, blank=True, default=''
    )
    wekan_password = models.CharField(
        verbose_name=_('Wekan Password'), max_length=100, blank=True, default=''
    )
    wekan_board_id = models.CharField(
        verbose_name=_('Wekan Board ID'), max_length=42, blank=True, default='',
        help_text=_("ID of the Wekan Board for Tech Rider sync (e.g. taken from the Boards's URL in a "
                    'browser).')
    )
    wekan_list_title = models.CharField(
        verbose_name=_('Wekan Initial List Title'), max_length=100, blank=True, default='',
        help_text=_('Title/name of the Wekan List to which new Cards for Tech Riders get added.')
    )
    wekan_swimlane_title = models.CharField(
        verbose_name=_('Wekan Initial Swimlane Title'), max_length=100, blank=True, default='Default',
        help_text=_('Title/name of the Wekan Swimlane to which new Cards for Tech Riders get added.')
    )

    objects = ScopedManager(event='event')

    def __str__(self):
        return f'SamAwareSettings(event={self.event.slug})'

    def get_wekan_server(self):
        logger = logging.getLogger(__name__)

        if not self.wekan_base_url:
            logger.warning('Base URL not set, cannot sync Tech Riders for "%s" to Wekan', self.event.name)
            return None

        return wekan.RealWekanServer(self.wekan_base_url)

    def get_wekan_syncer(self, wekan_server):
        logger = logging.getLogger(__name__)

        for attr in ('wekan_username', 'wekan_password', 'wekan_board_id', 'wekan_list_title',
                     'wekan_swimlane_title'):
            if not getattr(self, attr):
                verbose_name = self._meta.get_field(attr).verbose_name
                logger.warning('%s not set, cannot sync Tech Riders for "%s" to Wekan', verbose_name,
                               self.event.name)
                return None

        return wekan.WekanSyncer(wekan_server, self.wekan_username, self.wekan_password, self.wekan_board_id,
                                 self.wekan_list_title, self.wekan_swimlane_title)


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
    sync_dirty = models.BooleanField(default=True, editable=False)
    sync_info = models.JSONField(default=dict, editable=False)
    last_sync = models.DateTimeField(null=True, default=None)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = ScopedManager(event='event')

    def __str__(self):
        return f'TechRider(event={self.event.slug}, submission={self.submission})'

    def get_absolute_url(self):
        return reverse('plugins:samaware:tech_rider_update', kwargs={'event': self.event.slug,
                                                                     'pk': self.pk})

    def sync_to_wekan(self, wekan_syncer):
        """
        Forces sync of the Rider to Wekan, regardless of its dirty status, previous sync, etc.
        """
        # pylint: disable=E1135, E1136, E1137
        if 'wekan_card_ids' not in self.sync_info:
            self.sync_info['wekan_card_ids'] = {}

        for slot in self.event.wip_schedule.talks.filter(submission=self.submission):
            time_str = slot.start.astimezone(self.event.tz).strftime('%Y-%m-%d - %H:%M')
            title = f'[{slot.room.name} - {time_str}] {self.submission.title}'

            labels = [str(slot.room.name)]
            if self.submission.do_not_record:
                labels.append('Do not record')

            # Everything here will be JSON-serialized, so use strs as keys don't use defaultdicts
            if card_id := self.sync_info['wekan_card_ids'].get(str(slot.pk)):
                wekan_syncer.update_card(card_id, title, self.text, slot.start, labels)
            else:
                card_id = wekan_syncer.add_card(title, self.text, slot.start, labels)
                self.sync_info['wekan_card_ids'][str(slot.pk)] = card_id

            self.sync_dirty = False
            self.last_sync = timezone.now()
            self.save()

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
        speaker_name = self.speaker.get_display_name()
        return f'SpeakerCareMessage(event={self.event.slug}, user={speaker_name})'

    def get_absolute_url(self):
        return reverse('plugins:samaware:care_message_update', kwargs={'event': self.event.slug,
                                                                       'pk': self.pk})
