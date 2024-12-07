from django.urls import re_path
from pretalx.event.models.event import SLUG_REGEX

from . import views

urlpatterns = [
    re_path(
        rf'^orga/event/(?P<event>{SLUG_REGEX})/p/samaware/$',
        views.Dashboard.as_view(),
        name='dashboard'
    ),
    re_path(
        rf'^orga/event/(?P<event>{SLUG_REGEX})/p/samaware/missing-speakers/$',
        views.MissingSpeakersList.as_view(),
        name='missing_speakers'
    ),
    re_path(
        rf'^orga/event/(?P<event>{SLUG_REGEX})/p/samaware/no-recording/$',
        views.NoRecordingList.as_view(),
        name='no_recording'
    )
]
