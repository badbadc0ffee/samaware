from django.urls import path

from . import views

urlpatterns = [
    path(
        'orga/event/<slug:event>/p/samaware/',
        views.Dashboard.as_view(),
        name='dashboard'
    ),
    path(
        'orga/event/<slug:event>/p/samaware/talks/<code>',
        views.TalkOverview.as_view(),
        name='talk_overview'
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
    ),
    path(
        'orga/event/<slug:event>/p/samaware/fragments/search',
        views.SearchFragment.as_view(),
        name='search_fragment'
    ),
    path(
        'orga/event/<slug:event>/p/samaware/fragments/internal-notes/<code>',
        views.InternalNotesFragment.as_view(),
        name='internal_notes_fragment'
    )
]
