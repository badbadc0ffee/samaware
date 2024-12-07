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


def get_slots_missing_speakers(event, timeframe):
    """
    Returns TalkSlots that start within the specified timeframe from now but have speakers who have not yet
    been marked as arrived.
    """

    now = timezone.now()
    upcoming_threshold = now + timeframe
    upcoming_slots = event.wip_schedule.talks.filter(start__gt=now, start__lt=upcoming_threshold)

    unarrived_speakers = SpeakerProfile.objects.filter(event=event,
                                                       has_arrived=False).values_list('user', flat=True)

    return upcoming_slots.filter(submission__speakers__in=unarrived_speakers,
                                 submission__state__in=SubmissionStates.accepted_states)


def get_slots_without_recording(event, timeframe=None):
    """
    Returns TalkSlots whose talk has "Don't record" set, optionally starting within a specified timeframe.
    """

    slots = event.wip_schedule.talks.filter(submission__do_not_record=True,
                                            submission__state__in=SubmissionStates.accepted_states)

    if timeframe is None:
        return slots
    else:
        now = timezone.now()
        upcoming_threshold = now + timeframe

        return slots.filter(start__gt=now, start__lt=upcoming_threshold)
