from itertools import chain

from django.utils import timezone
from django_scopes import scopes_disabled
from pretalx.person.models import SpeakerProfile
from pretalx.submission.models.submission import Submission, SubmissionManager, SubmissionStates


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


def get_slots_missing_speakers(event, timeframe=None):
    """
    Returns TalkSlots that have speakers who have not yet been marked as arrived, optionally starting within
    a specified timeframe from now.
    """

    unarrived_speakers = SpeakerProfile.objects.filter(event=event,
                                                       has_arrived=False).values_list('user', flat=True)
    slots = event.wip_schedule.talks.filter(submission__speakers__in=unarrived_speakers,
                                            submission__state__in=SubmissionStates.accepted_states)
    slots = slots.distinct()

    if timeframe is None:
        return slots
    else:
        now = timezone.now()
        upcoming_threshold = now + timeframe
        return slots.filter(start__gt=now, start__lt=upcoming_threshold)


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


def get_unreleased_changes_for_submission(submission):
    """
    Returns a list of changes for the given talk between the current WiP Schedule and the previous
    (released) one.
    """

    schedule_changes = submission.event.wip_schedule.changes

    # Contains TalkSlots
    new_changes = filter(lambda s: s.submission == submission, schedule_changes['new_talks'])
    # Contains TalkSlots
    canceled_changes = filter(lambda s: s.submission == submission, schedule_changes['canceled_talks'])
    # Contains dicts containing the submission
    moved_changes = filter(lambda d: d['submission'] == submission, schedule_changes['moved_talks'])

    return list(chain(new_changes, canceled_changes, moved_changes))


def get_talks_in_other_events(user, event):
    """
    Returns a list of accepted Submissions where the given User is among the speakers, across all public
    Events from the current pretalx instance.
    To avoid having to deal with permissions on the other Events, we limit ourselves to talks that are
    visible in a published Schedule.
    """

    class AllEventsSubmission(Submission):
        """
        Proxy Model for `pretalx.submission.models.Submission` which overwrites the default Manager with
        one *not* scoped to an Event.
        """
        objects = SubmissionManager()

        class Meta:
            proxy = True

    with scopes_disabled():
        submissions = AllEventsSubmission.objects.filter(
            speakers=user, state__in=SubmissionStates.accepted_states, event__is_public=True
        ).exclude(event=event).order_by('-created').select_related('event')

        # Check if submissions is really contained in the latest published Schedule: There might be no
        # (public) schedule at all or it might be accepted but not scheduled (and therefore not publicly
        # visible)
        submissions_list = [s for s in submissions if s in s.event.talks]

    return submissions_list
