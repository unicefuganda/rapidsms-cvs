from django.shortcuts import get_object_or_404
from rapidsms.contrib.locations.models import Location
from django.utils.datastructures import SortedDict
from uganda_common.views import XFormChartView
from cvs.utils import active_reporters

class ActiveReportersChartView(XFormChartView):
    chart_title = 'Variation of Active Reporters'
    roles = ['VHT', 'PVHT']
    period = 1

    def get_data(self):
        location = get_object_or_404(Location, pk=self.location_id)
        group_by = self.get_group_by(self.start_date, self.end_date)

        data = active_reporters(self.start_date, self.end_date, location, roles=self.roles, group_by_timespan=group_by['group_by'], period=self.period)
        chart_data = list(data)
        chart_data = self.reorganize_for_chart_api(group_by['group_by_name'], chart_data)

        json_response_data = {'series':list(chart_data), \
                              'timespan':group_by['group_by_name'], \
                              'title':self.get_chart_title(), \
                              'subtitle':self.get_chart_subtitle(), \
                              'yaxis':self.get_y_axis(), \
                              }
        return json_response_data



