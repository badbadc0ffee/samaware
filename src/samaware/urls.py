from django.urls import path

from . import views

urlpatterns = [
    path(
        'orga/event/<slug:event>/p/samaware/',
        views.Dashboard.as_view(),
        name='dashboard'
    ),
    path(
        'orga/event/<slug:event>/p/samaware/missing-speakers/',
        views.MissingSpeakersList.as_view(),
        name='missing_speakers'
    ),
    path(
        'orga/event/<slug:event>/p/samaware/no-recording/',
        views.NoRecordingList.as_view(),
        name='no_recording'
    )
]
