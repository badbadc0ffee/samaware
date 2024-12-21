from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_scopes import ScopedManager
from pretalx.event.models import Event
from pretalx.person.models import User


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
