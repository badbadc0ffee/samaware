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

    def test_sessions_missing_speakers(self):
        timeframe = timedelta(hours=2)

        with scope(event=self.event):
            sessions = queries.get_sessions_missing_speakers(self.event, timeframe)

        self.assertEqual(len(sessions), 2)

        with scope(event=self.event):
            for speaker in sessions[0].speaker_profiles:
                speaker.has_arrived = True
                speaker.save()

            sessions = queries.get_sessions_missing_speakers(self.event, timeframe)

        self.assertEqual(len(sessions), 1)

    def test_sessions_missing_speakers_multi(self):
        timeframe = timedelta(days=5)

        with scope(event=self.event):
            sessions = queries.get_sessions_missing_speakers(self.event, timeframe)

        self.assertEqual(len(sessions), 6)

        with scope(event=self.event):
            for session in sessions:
                if len(session.speaker_profiles) == 1:
                    session.speaker_profiles[0].has_arrived = True
                    session.speaker_profiles[0].save()

            sessions = queries.get_sessions_missing_speakers(self.event, timeframe)

        self.assertEqual(len(sessions), 1)

        with scope(event=self.event):
            changes_count = 0

            for speaker in sessions[0].speaker_profiles:
                if not speaker.has_arrived:
                    speaker.has_arrived = True
                    speaker.save()
                    changes_count += 1

            sessions = queries.get_sessions_missing_speakers(self.event, timeframe)

        self.assertEqual(len(sessions), 0)
        self.assertEqual(changes_count, 1)

    def test_sessions_without_recording(self):
        with scope(event=self.event):
            sessions = queries.get_sessions_without_recording(self.event)

        self.assertEqual(len(sessions), 2)

        timeframe = timedelta(hours=2)
        with scope(event=self.event):
            sessions = queries.get_sessions_without_recording(self.event, timeframe)

        self.assertEqual(len(sessions), 1)
