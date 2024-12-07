from datetime import timedelta

from django_scopes import scope
from pretalx.person.models.profile import SpeakerProfile

from samaware import queries

from .lib import SamawareTestCase


class QueriesTest(SamawareTestCase):

    def test_all_speakers(self):
        with scope(event=self.event):
            speakers = queries.get_all_speakers(self.event)

        self.assertEqual(len(speakers), 5)

        speaker_names = [s.user.name for s in speakers]
        self.assertIn('Richard Khan', speaker_names)
        self.assertNotIn('Donna Bailey', speaker_names)

    def test_arrived_speakers(self):
        with scope(event=self.event):
            tammy = SpeakerProfile.objects.get(id=2)
            tammy.has_arrived = True
            tammy.save()

            speakers = queries.get_arrived_speakers(self.event)

        self.assertEqual(len(speakers), 1)
        self.assertEqual(speakers[0].user.name, 'Tammy Wong')

    def test_slots_missing_speakers(self):
        timeframe = timedelta(hours=2)

        with scope(event=self.event):
            slots = queries.get_slots_missing_speakers(self.event, timeframe)

        self.assertEqual(len(slots), 2)

        with scope(event=self.event):
            for speaker in slots[0].submission.speaker_profiles:
                speaker.has_arrived = True
                speaker.save()

            slots = queries.get_slots_missing_speakers(self.event, timeframe)

        self.assertEqual(len(slots), 1)

    def test_slots_missing_speakers_multi(self):
        with scope(event=self.event):
            slots = queries.get_slots_missing_speakers(self.event)

        self.assertEqual(len(slots), 5)

        with scope(event=self.event):
            for slot in slots:
                if len(slot.submission.speaker_profiles) == 1:
                    slot.submission.speaker_profiles[0].has_arrived = True
                    slot.submission.speaker_profiles[0].save()

            slots = queries.get_slots_missing_speakers(self.event)

        self.assertEqual(len(slots), 1)

        with scope(event=self.event):
            changes_count = 0

            for speaker in slots[0].submission.speaker_profiles:
                if not speaker.has_arrived:
                    speaker.has_arrived = True
                    speaker.save()
                    changes_count += 1

            slots = queries.get_slots_missing_speakers(self.event)

        self.assertEqual(len(slots), 0)
        self.assertEqual(changes_count, 1)

    def test_slots_without_recording(self):
        with scope(event=self.event):
            slots = queries.get_slots_without_recording(self.event)

        self.assertEqual(len(slots), 2)

        timeframe = timedelta(hours=2)
        with scope(event=self.event):
            slots = queries.get_slots_without_recording(self.event, timeframe)

        self.assertEqual(len(slots), 1)
