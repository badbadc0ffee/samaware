from datetime import timedelta

from django.db.models import Min
from django.test import TestCase
from django.utils import timezone
from django_scopes import scopes_disabled
from pretalx.event.models import Event
from pretalx.schedule.models.slot import TalkSlot


class SamawareTestCase(TestCase):

    fixtures = ['samaware']

    @classmethod
    def setUpClass(cls):
        # See also django-scopes docs, though the monkeypatch described there neither worked, nor appeared
        # necessary: https://github.com/raphaelm/django-scopes/blob/5ca2a14/README.md#testing
        with scopes_disabled():
            super().setUpClass()

    def setUp(self):
        super().setUp()

        with scopes_disabled():
            self.event = Event.objects.get()
            slots_to_edit = TalkSlot.objects.filter(schedule__gt=1)

            earliest_start = slots_to_edit.aggregate(Min('start'))['start__min']
            offset = timezone.now() - earliest_start + timedelta(minutes=10)

            # Make all talks start today or tomorrow
            for slot in slots_to_edit:
                slot.start += offset
                slot.end += offset
                slot.save()
