from django.test import Client
from django.urls import reverse
from django_scopes import scope
from pretalx.person.models.user import User

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
