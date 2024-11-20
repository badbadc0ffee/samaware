import datetime

from django.views.generic.base import TemplateView

from pretalx.common.views.mixins import EventPermissionRequired

import samaware

from . import queries


class DashboardView(EventPermissionRequired, TemplateView):

    permission_required = samaware.required_permissions
    template_name = 'samaware/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['total_speakers'] = queries.get_all_speakers(self.request.event)
        context['arrived_speakers'] = queries.get_arrived_speakers(self.request.event)
        context['unreleased_changes'] = self.request.event.wip_schedule.changes

        timeframe = datetime.timedelta(hours=4)
        context['sessions_missing_speakers'] = queries.get_sessions_missing_speakers(self.request.event,
                                                                                     timeframe)

        return context
