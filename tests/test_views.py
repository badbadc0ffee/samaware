from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django_scopes import scope
from pretalx.person.models.user import User
from pretalx.schedule.models import TalkSlot
from pretalx.submission.models import Submission, SubmissionStates

from samaware.models import SpeakerCareMessage, TechRider

from .lib import SamawareTestCase


class ViewsTestCase(SamawareTestCase):

    def setUp(self):
        super().setUp()

        self.client = Client()
        self.admin = User.objects.get(email='admin@example.org')
        self.client.force_login(self.admin)


class DashboardTest(ViewsTestCase):

    def test_dashboard(self):
        response = self.client.get(reverse('plugins:samaware:dashboard', kwargs={'event': self.event.slug}))

        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['total_speakers']), 5)
        self.assertEqual(len(response.context['slots_missing_speakers']), 2)

        # htmx requires this, see comment in "views.py" for details
        self.assertIn("script-src 'self' 'unsafe-eval'", response.headers['Content-Security-Policy'])


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

    def test_default(self):
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 2)

    def test_upcoming(self):
        response = self.client.get(self.path + '?upcoming=on')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 1)

    def test_no_rider(self):
        response = self.client.get(self.path + '?no_rider=on')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 2)

        with scope(event=self.event):
            submission = self.event.talks.filter(do_not_record=True).first()
            rider = TechRider(event=self.event, author=self.admin, submission=submission,
                              text='We are gonna need > 9000 couches on stage.')
            rider.save()

        response = self.client.get(self.path + '?no_rider=on')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 1)


class TechRiderTest(ViewsTestCase):

    def setUp(self):
        super().setUp()

        with scope(event=self.event):
            self.submission = Submission.objects.get(id=1, event=self.event)

    def add_rider(self):
        with scope(event=self.event):
            rider = TechRider(event=self.event, author=self.admin, submission=self.submission,
                              text='We are gonna need > 9000 couches on stage.')
            rider.save()

        return rider

    def test_list(self):
        path = reverse('plugins:samaware:tech_rider_list', kwargs={'event': self.event.slug})

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 0)

        self.add_rider()
        with scope(event=self.event):
            submission_4 = Submission.objects.get(id=4, event=self.event)
            rider = TechRider(event=self.event, author=self.admin, submission=submission_4,
                              text='If the others get them, we also want couches!')
            rider.save()

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 2)

        response = self.client.get(path + '?upcoming=on')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['slots']), 1)

    def test_create(self):
        path = reverse('plugins:samaware:tech_rider_create', kwargs={'event': self.event.slug})

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('object', response.context)

        text = 'Lorem ipsum dolor sit amet, consetetur sadipscing elitr.'
        response = self.client.post(path, {'submission': self.submission.pk, 'text': text})
        self.assertEqual(response.status_code, 302)

        with scope(event=self.event):
            riders = self.event.tech_riders.all()

        self.assertEqual(len(riders), 1)
        self.assertEqual(riders[0].submission, self.submission)
        self.assertEqual(riders[0].text, text)
        self.assertEqual(riders[0].author, self.admin)

    def test_update(self):
        rider = self.add_rider()

        path = reverse('plugins:samaware:tech_rider_update', kwargs={'event': self.event.slug,
                                                                     'pk': rider.pk})

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], rider)

        text = 'Lorem ipsum dolor sit amet, consetetur sadipscing elitr.'
        response = self.client.post(path, {'submission': rider.submission.pk, 'text': text})  # pylint: disable=E1101
        self.assertEqual(response.status_code, 302)

        with scope(event=self.event):
            riders = self.event.tech_riders.all()

        self.assertEqual(len(riders), 1)
        self.assertEqual(riders[0].text, text)

    def test_delete(self):
        rider = self.add_rider()

        path = reverse('plugins:samaware:tech_rider_delete', kwargs={'event': self.event.slug,
                                                                     'pk': rider.pk})

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)

        with scope(event=self.event):
            riders = self.event.tech_riders.all()

        self.assertEqual(len(riders), 1)

        response = self.client.post(path)
        self.assertEqual(response.status_code, 302)

        with scope(event=self.event):
            riders = self.event.tech_riders.all()

        self.assertEqual(len(riders), 0)

    def test_no_permission(self):
        rider = self.add_rider()

        self.client.logout()
        self.client.force_login(self.submission.speakers.first())

        path = reverse('plugins:samaware:tech_rider_update', kwargs={'event': self.event.slug,
                                                                     'pk': rider.pk})
        response = self.client.post(path, {'submission': self.submission.pk,
                                           'text': 'Hello from the speaker'})

        self.assertEqual(response.status_code, 404)


class CareMessageTest(ViewsTestCase):

    def setUp(self):
        super().setUp()

        with scope(event=self.event):
            self.submission = Submission.objects.get(id=1, event=self.event)
            self.speaker = self.submission.speakers.first()

    def add_message(self):
        with scope(event=self.event):
            message = SpeakerCareMessage(event=self.event, author=self.admin, speaker=self.speaker,
                                         text='This is an important announcement.')
            message.save()

        return message

    def test_list(self):
        path = reverse('plugins:samaware:care_message_list', kwargs={'event': self.event.slug})

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['care_messages']), 0)

        self.add_message()

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['care_messages']), 1)
        self.assertEqual(response.context['care_messages'][0].speaker, self.speaker)
        self.assertEqual(len(response.context['speaker_talks'][self.speaker]), 1)
        self.assertEqual(response.context['speaker_talks'][self.speaker][0], self.submission)
        self.assertEqual(response.context['speaker_first_slots'][self.speaker].submission, self.submission)

    def test_list_sort(self):
        self.add_message()

        with scope(event=self.event):
            speaker_2 = User.objects.get(id=5)
            message_2 = SpeakerCareMessage(event=self.event, author=self.admin, speaker=speaker_2,
                                         text='Another very important announcement.')
            message_2.save()

        path = reverse('plugins:samaware:care_message_list', kwargs={'event': self.event.slug})

        response = self.client.get(path + '?sort=-_first_talk_start')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(len(response.context['care_messages']), 2)
        self.assertGreater(
            response.context['speaker_first_slots'][response.context['care_messages'][0].speaker].start,
            response.context['speaker_first_slots'][response.context['care_messages'][1].speaker].start
        )
        self.assertEqual(response.context['care_messages'][0].text, 'Another very important announcement.')
        self.assertEqual(response.context['care_messages'][1].text, 'This is an important announcement.')

    def test_create(self):
        path = reverse('plugins:samaware:care_message_create', kwargs={'event': self.event.slug})

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('object', response.context)

        text = 'Lorem ipsum dolor sit amet, consetetur sadipscing elitr.'
        response = self.client.post(path, {'speaker': self.speaker.pk, 'text': text})
        self.assertEqual(response.status_code, 302)

        with scope(event=self.event):
            messages = self.event.speaker_care_messages.all()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].speaker, self.speaker)
        self.assertEqual(messages[0].text, text)
        self.assertEqual(messages[0].author, self.admin)

    def test_update(self):
        message = self.add_message()

        path = reverse('plugins:samaware:care_message_update', kwargs={'event': self.event.slug,
                                                                       'pk': message.pk})

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], message)

        text = 'Lorem ipsum dolor sit amet, consetetur sadipscing elitr.'
        response = self.client.post(path, {'speaker': message.speaker.pk, 'text': text})  # pylint: disable=E1101
        self.assertEqual(response.status_code, 302)

        with scope(event=self.event):
            messages = self.event.speaker_care_messages.all()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].text, text)

    def test_delete(self):
        message = self.add_message()

        path = reverse('plugins:samaware:care_message_delete', kwargs={'event': self.event.slug,
                                                                       'pk': message.pk})

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)

        with scope(event=self.event):
            messages = self.event.speaker_care_messages.all()

        self.assertEqual(len(messages), 1)

        response = self.client.post(path)
        self.assertEqual(response.status_code, 302)

        with scope(event=self.event):
            messages = self.event.speaker_care_messages.all()

        self.assertEqual(len(messages), 0)

    def test_talk_overview(self):
        self.add_message()
        with scope(event=self.event):
            submission = Submission.objects.filter(event=self.event, speakers=self.speaker).first()

        path = reverse('plugins:samaware:talk_overview', kwargs={'event': self.event.slug,
                                                                 'code': submission.code})
        response = self.client.get(path)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['speaker_care_messages']), 1)
        self.assertContains(response, 'Speaker Care Message available')


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


class TechRiderFragmentTest(ViewsTestCase):

    def setUp(self):
        super().setUp()

        with scope(event=self.event):
            self.submission = Submission.objects.get(id=1, event=self.event)

        self.path = reverse('plugins:samaware:tech_rider_fragment',
                            kwargs={'event': self.event.slug, 'code': self.submission.code})

    def test_get(self):
        response = self.client.get(self.path)

        self.assertEqual(response.status_code, 200)

        self.assertNotIn('object', response.context)
        self.assertEqual(response.context['form']['submission'].widget_type, 'hidden')
        self.assertContains(response, 'Tech Rider')
        self.assertContains(response, '<form')

    def test_post(self):
        text = 'SCART video input is required on stage.'
        response = self.client.post(self.path, {'submission': self.submission.pk, 'text': text})

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, text)
        self.assertNotContains(response, '<form')

        with scope(event=self.event):
            rider = self.event.tech_riders.get(submission=self.submission)

        self.assertEqual(rider.text, text)
