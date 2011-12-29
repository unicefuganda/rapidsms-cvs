from uganda_common.views import XFormReport

class CVSReportView(XFormReport):
    partial_base = 'cvs/partials/stats_partial_base.html'

    drill_to_facility = False

    def drill_on(self, key):
        XFormReport.drill_on(self, key)
        while self.location.get_children().count() == 1 and not self.location.type == 'sub_county':
            # drill again as long as there's only one child
            self.location = self.location.get_children()[0]

        if self.location.type.name == 'sub_county':
            self.partial_row = 'cvs/partials/stats_row.html'
            self.drill_to_facility = True
