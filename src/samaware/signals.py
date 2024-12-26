import logging

from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _
from django_scopes import scopes_disabled
from pretalx.common.signals import EventPluginSignal, minimum_interval, periodic_task
from pretalx.orga.signals import nav_event, nav_event_settings

import samaware

from . import models

speaker_html = EventPluginSignal()
submission_html = EventPluginSignal()


@receiver(nav_event, dispatch_uid='samaware_nav')
def navbar_info(sender, request, **kwargs):  # noqa: ARG001, pylint: disable=W0613

    if not request.user.has_perm(samaware.REQUIRED_PERMISSIONS, request.event):
        return []

    url = resolve(request.path_info)

    return [{
        'label': 'SamAware',
        'icon': 'samaware/icon.svg',
        'url': reverse('plugins:samaware:dashboard', kwargs={'event': request.event.slug}),
        'active': url.namespace == 'plugins:samaware',
        'children': [{
            'label': _('Talks missing speakers'),
            'url': reverse('plugins:samaware:missing_speakers', kwargs={'event': request.event.slug}),
            'active': url.namespace == 'plugins:samaware' and url.url_name == 'missing_speakers',
        }, {
            'label': _('Talks without recording'),
            'url': reverse('plugins:samaware:no_recording', kwargs={'event': request.event.slug}),
            'active': url.namespace == 'plugins:samaware' and url.url_name == 'no_recording',
        },  {
            'label': _('Tech Riders'),
            'url': reverse('plugins:samaware:tech_rider_list', kwargs={'event': request.event.slug}),
            'active': url.namespace == 'plugins:samaware' and url.url_name == 'tech_rider_list',
        }, {
            'label': _('Speaker Care Messages'),
            'url': reverse('plugins:samaware:care_message_list', kwargs={'event': request.event.slug}),
            'active': url.namespace == 'plugins:samaware' and url.url_name == 'care_message_list',
        }]
    }]


@receiver(nav_event_settings, dispatch_uid='samaware_nav_settings')
def navbar_settings(sender, request, **kwargs):  # noqa: ARG001, pylint: disable=W0613

    if not request.user.has_perm('orga.change_settings', request.event):
        return []

    return [{
        'label': 'SamAware',
        'url': reverse('plugins:samaware:settings', kwargs={'event': request.event.slug}),
        'active': request.resolver_match.url_name == 'plugins:samaware:settings'
    }]


@receiver(periodic_task)
@minimum_interval(minutes_after_success=5)
def full_wekan_sync(sender, **kwargs):  # noqa: ARG001, pylint: disable=W0613

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    def get_syncer(event):
        if (settings := models.SamAwareSettings.objects.filter(event=event).first()) is None:
            logging.warning('Wekan settings not configured for event "%s", skipping Tech Rider sync',
                            event.name)
            return None

        if (server := settings.get_wekan_server()) is None:
            return None
        return settings.get_wekan_syncer(server)

    event_syncers = {}

    with scopes_disabled():
        for rider in models.TechRider.objects.all():
            try:
                syncer = event_syncers[rider.event]
            except KeyError:
                syncer = get_syncer(rider.event)
                event_syncers[rider.event] = syncer

            if syncer is None:
                continue

            try:
                rider.sync_to_wekan(syncer)
            except:  # noqa: E722, pylint: disable=W0702
                logger.exception('Error syncing Tech Rider for "%s" to Wekan:', rider.submission.title)
            else:
                logger.info('Successfully synced Tech Rider for "%s" to Wekan', rider.submission.title)
