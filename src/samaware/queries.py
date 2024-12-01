from django.utils import timezone
from pretalx.person.models import SpeakerProfile
from pretalx.submission.models import SubmissionStates


def get_all_speakers(event):
    """
    Returns the SpeakerProfiles of all users who have an accepted talk in the current event.
    This is different from `event.speakers` because the latter only returns speakers from the current
    released schedule, whereas this considers the current submission states.
    """

    accepted_submissions = event.submissions.filter(state__in=SubmissionStates.accepted_states)
    profiles = SpeakerProfile.objects.filter(user__submissions__in=accepted_submissions)

    return profiles.distinct()


def get_arrived_speakers(event):
    """
    Returns the SpeakerProfiles of all users who have an accepted talk in the current event and have been
    marked as arrived at the venue.
    """

    return get_all_speakers(event).filter(has_arrived=True)


def get_sessions_missing_speakers(event, timeframe):
    """
    Returns sessions (i.e. Submissions) that start within the specified timeframe from now but have speakers
    who have not yet been marked as arrived.
    """

    now = timezone.now()
    upcoming_threshold = now + timeframe
    upcoming_slots = event.wip_schedule.talks.filter(start__gt=now, start__lt=upcoming_threshold)

    unarrived_speakers = SpeakerProfile.objects.filter(event=event,
                                                       has_arrived=False).values_list('user', flat=True)

    return event.submissions.filter(state__in=SubmissionStates.accepted_states,
                                    slots__in=upcoming_slots,
                                    speakers__in=unarrived_speakers)
