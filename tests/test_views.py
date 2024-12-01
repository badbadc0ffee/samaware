from django.test import Client
from django.urls import reverse
from pretalx.person.models.user import User

from .lib import SamawareTestCase


class DashboardTest(SamawareTestCase):

    def setUp(self):
        super().setUp()

        self.client = Client()
        admin = User.objects.get(email='admin@example.org')
        self.client.force_login(admin)

    def test_dashboard(self):
        response = self.client.get(reverse('plugins:samaware:dashboard', kwargs={'event': self.event.slug}))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['total_speakers']), 5)
        self.assertEqual(len(response.context['sessions_missing_speakers']), 2)
