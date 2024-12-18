from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django_scopes import scope
from pretalx.person.models.user import User
from pretalx.schedule.models import TalkSlot
from pretalx.submission.models import Submission, SubmissionStates

from .lib import SamawareTestCase


class ViewsTestCase(SamawareTestCase):

    def setUp(self):
        super().setUp()

        self.client = Client()
        admin = User.objects.get(email='admin@example.org')
        self.client.force_login(admin)


class DashboardTest(ViewsTestCase):

    def test_dashboard(self):
        response = self.client.get(reverse('plugins:samaware:dashboard', kwargs={'event': self.event.slug}))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['total_speakers']), 5)
        self.assertEqual(len(response.context['slots_missing_speakers']), 2)

        # htmx requires this, see comment in "views.py" for details
        self.assertIn("script-src 'self' 'unsafe-eval';", response.headers['Content-Security-Policy'])


class TalkOverviewTest(ViewsTestCase):

    def setUp(self):
        super().setUp()

        with scope(event=self.event):
            self.submission = Submission.objects.get(id=1, event=self.event)
            self.speaker = self.submission.speakers.first()

        self.path = reverse('plugins:samaware:talk_overview', kwargs={'event': self.event.slug,
                                                                      'code': self.submission.code})

    def test_overview(self):
        with scope(event=self.event):
            profile = self.speaker.event_profile(self.event)

        response = self.client.get(self.path)

        self.assertEqual(response.status_code, 200)

        self.assertTrue(response.context['submission_is_confirmed'])
        self.assertEqual(len(response.context['submission_unreleased_changes']), 0)
        self.assertEqual(len(response.context['submission_wip_slots']), 1)
        self.assertEqual(len(response.context['speaker_profiles']), 1)
        self.assertEqual(response.context['speaker_profiles'][self.speaker], profile)
        self.assertEqual(len(response.context['other_event_talks'][self.speaker]), 0)

        self.assertContains(response, 'Being streamed/recorded')
        self.assertContains(response, 'Mark as arrived')

        arrived_url = reverse('orga:speakers.arrived', kwargs={'event': self.submission.event.slug,
                                                               'code': self.speaker.code})
        self.assertContains(response, f'<form action="{arrived_url}"')

    def test_unreleased_changes(self):
        with scope(event=self.event):
            slot = TalkSlot.objects.get(submission=self.submission, schedule=self.event.wip_schedule)
            slot.start = slot.start + timedelta(minutes=15)
            slot.end = slot.end + timedelta(minutes=15)
            slot.save()

            self.submission.do_not_record = True
            self.submission.save()

        response = self.client.get(self.path)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['submission_unreleased_changes']), 1)
        self.assertContains(response, 'unreleased schedule changes')

        self.assertContains(response, 'Not being streamed/recorded')

    def test_canceled(self):
        with scope(event=self.event):
            submission = Submission.objects.get(state=SubmissionStates.CANCELED, event=self.event)

        path = reverse('plugins:samaware:talk_overview', kwargs={'event': self.event.slug,
                                                                 'code': submission.code})
        response = self.client.get(path)

        self.assertEqual(response.status_code, 200)

        self.assertFalse(response.context['submission_is_confirmed'])
        self.assertContains(response, 'not in state confirmed')


class MissingSpeakersListTest(ViewsTestCase):

    def setUp(self):
        super().setUp()
        self.path = reverse('plugins:samaware:missing_speakers', kwargs={'event': self.event.slug})

    def test_upcoming_off(self):
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 5)

        with scope(event=self.event):
            for slot in response.context['slots']:
                for user in slot.submission.speakers.all():
                    self.assertIn(user, response.context['event_profiles'])

                for profile in slot.submission.speaker_profiles:
                    profile.has_arrived = True
                    profile.save()

        response = self.client.get(self.path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 0)

    def test_upcoming_on(self):
        response = self.client.get(self.path + '?upcoming=on')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 2)


class NoRecordingListTest(ViewsTestCase):

    def setUp(self):
        super().setUp()
        self.path = reverse('plugins:samaware:no_recording', kwargs={'event': self.event.slug})

    def test_upcoming_off(self):
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 2)

    def test_upcoming_on(self):
        response = self.client.get(self.path + '?upcoming=on')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 1)


class SearchFragmentTest(ViewsTestCase):

    def setUp(self):
        super().setUp()
        self.path = reverse('plugins:samaware:search_fragment', kwargs={'event': self.event.slug})

    def test_no_query(self):
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 5)

        for slot in response.context['slots']:
            for user in slot.submission.speakers.all():
                self.assertIn(user, response.context['event_profiles'])

    def test_submission_query(self):
        response = self.client.get(self.path + '?query=ReCiPrOcAl')

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['slots']), 1)
        self.assertEqual(response.context['slots'][0].submission.code, 'H7HMGF')

    def test_speaker_query(self):
        response = self.client.get(self.path + '?query=richard')

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['slots']), 1)
        self.assertEqual(response.context['slots'][0].submission.code, 'M89B9Q')


class InternalNotesFragmentTest(ViewsTestCase):

    def setUp(self):
        super().setUp()

        with scope(event=self.event):
            self.submission = Submission.objects.get(id=1, event=self.event)

        self.path = reverse('plugins:samaware:internal_notes_fragment',
                            kwargs={'event': self.event.slug, 'code': self.submission.code})

    def test_get(self):
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context['object'], self.submission)
        self.assertContains(response, 'Internal Notes')
        self.assertContains(response, '<form')

    def test_post(self):
        note = 'Hello from the otter slide'
        response = self.client.post(self.path, {'internal_notes': note})

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, note)
        self.assertNotContains(response, '<form')

        with scope(event=self.event):
            submission = Submission.objects.get(id=self.submission.id)

        self.assertEqual(submission.internal_notes, note)
