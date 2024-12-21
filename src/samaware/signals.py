from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _
from pretalx.orga.signals import nav_event

import samaware


@receiver(nav_event, dispatch_uid='samaware_nav')
def navbar_info(sender, request, **kwargs):  # noqa: ARG001, pylint: disable=W0613

    if not request.user.has_perm(samaware.REQUIRED_PERMISSIONS, request.event):
        return []

    url = resolve(request.path_info)

    return [{
        'label': 'SamAware',
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
