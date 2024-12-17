from datetime import timedelta

from django_scopes import scope, scopes_disabled
from pretalx.event.models import Event
from pretalx.person.models import SpeakerProfile
from pretalx.schedule.models import Schedule, TalkSlot
from pretalx.submission.models import Submission, SubmissionStates

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

        with scope(event=self.event):
            submission = Submission.objects.get(state=SubmissionStates.REJECTED)
            submission.pending_state = SubmissionStates.ACCEPTED
            submission.save()

            speakers = queries.get_all_speakers(self.event)

        self.assertEqual(len(speakers), 6)

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

    def test_talks_in_other_events(self):
        with scopes_disabled():
            # Do a new query to get an independent reference
            new_event = Event.objects.get(id=self.event.id)
            new_event.pk = None
            new_event.name = '{"en": "SamAwareCon 2"}'
            new_event.slug = 'samawarecon-2'
            new_event.save()

            new_schedule = Schedule.objects.get(id=self.event.current_schedule.id)
            new_schedule.pk = None
            new_schedule.event = new_event
            new_schedule.save()

            old_submission = Submission.objects.get(id=1, event=self.event)
            new_submission = Submission.objects.get(id=1, event=self.event)
            new_submission.pk = None
            new_submission.event = new_event
            new_submission.code = old_submission.code[::-1]
            new_submission.review_code = old_submission.review_code[::-1]
            new_submission.save()
            new_submission.speakers.set(old_submission.speakers.all())

            new_slot = TalkSlot.objects.get(submission=old_submission, schedule=self.event.wip_schedule)
            new_slot.pk = None
            new_slot.schedule = new_schedule
            new_slot.submission = new_submission
            new_slot.save()

            speaker = old_submission.speakers.first()

        with scope(event=self.event):
            talks = queries.get_talks_in_other_events(speaker, self.event)

            self.assertEqual(len(talks), 1)
            self.assertEqual(talks[0], new_submission)


class UnreleasedChangesTest(SamawareTestCase):

    def test_moved(self):
        with scope(event=self.event):
            submission_1 = Submission.objects.get(id=1, event=self.event)
            submission_2 = Submission.objects.get(id=2, event=self.event)
            changes_1 = queries.get_unreleased_changes_for_submission(submission_1)
            changes_2 = queries.get_unreleased_changes_for_submission(submission_2)

        self.assertEqual(len(changes_1), 0)
        self.assertEqual(len(changes_2), 0)

        with scope(event=self.event):
            slot_1 = TalkSlot.objects.get(submission=submission_1, schedule=self.event.wip_schedule)
            slot_2 = TalkSlot.objects.get(submission=submission_2, schedule=self.event.wip_schedule)

            slot_1.start, slot_2.start = slot_2.start, slot_1.start
            slot_1.end, slot_2.end = slot_2.end, slot_1.end
            slot_1.save()
            slot_2.save()

            # Do new queries to re-evaluate all cached properties down the member hierarchy
            submission_1 = Submission.objects.get(id=1, event=self.event)
            submission_2 = Submission.objects.get(id=2, event=self.event)

            changes_1 = queries.get_unreleased_changes_for_submission(submission_1)
            changes_2 = queries.get_unreleased_changes_for_submission(submission_2)

        self.assertEqual(len(changes_1), 1)
        self.assertEqual(len(changes_2), 1)

    def test_canceled(self):
        with scope(event=self.event):
            submission_1 = Submission.objects.get(id=1, event=self.event)
            slot = TalkSlot.objects.get(submission=submission_1, schedule=self.event.wip_schedule)
            slot.delete()

            submission_1 = Submission.objects.get(id=1, event=self.event)
            submission_2 = Submission.objects.get(id=2, event=self.event)
            changes_1 = queries.get_unreleased_changes_for_submission(submission_1)
            changes_2 = queries.get_unreleased_changes_for_submission(submission_2)

        self.assertEqual(len(changes_1), 1)
        self.assertEqual(len(changes_2), 0)

    def test_new(self):
        with scope(event=self.event):
            canceled_submission = Submission.objects.get(state=SubmissionStates.CANCELED, event=self.event)
            rejected_submission = Submission.objects.get(state=SubmissionStates.REJECTED, event=self.event)

            slot = TalkSlot.objects.get(submission=canceled_submission, schedule=self.event.current_schedule)
            slot.pk = None
            slot.schedule = self.event.wip_schedule
            slot.submission = rejected_submission
            slot.save()

            rejected_submission.state = SubmissionStates.CONFIRMED
            rejected_submission.save()

            canceled_submission = Submission.objects.get(id=canceled_submission.id)
            rejected_submission = Submission.objects.get(id=rejected_submission.id)
            canceled_changes = queries.get_unreleased_changes_for_submission(canceled_submission)
            rejected_changes = queries.get_unreleased_changes_for_submission(rejected_submission)

        self.assertEqual(len(canceled_changes), 1)
        self.assertEqual(len(rejected_changes), 1)
