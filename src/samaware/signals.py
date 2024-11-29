from django.dispatch import receiver
from django.urls import resolve, reverse
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
        'active': url.namespace == 'plugins:samaware' and url.url_name == 'dashboard',
    }]