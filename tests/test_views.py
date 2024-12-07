from django.test import Client
from django.urls import reverse
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


class NoRecordingListTest(ViewsTestCase):

    def test_upcoming_off(self):

        response = self.client.get(reverse('plugins:samaware:no_recording',
                                           kwargs={'event': self.event.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 2)

    def test_upcoming_on(self):

        response = self.client.get(reverse('plugins:samaware:no_recording',
                                           kwargs={'event': self.event.slug}) + '?upcoming=on')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 1)
