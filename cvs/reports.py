from generic.reporting.views import ReportView
from generic.reporting.reports import Column
from uganda_common.reports import XFormAttributeColumn, XFormSubmissionColumn, QuotientColumn
from uganda_common.views import XFormReport
from .utils import active_reporters, registered_reporters
from uganda_common.utils import reorganize_location

COLUMN_TITLE_DICT = {
    'muac':'Total New Cases',
    'epi_ma':'Malaria',
    'epi_tb':'Tb',
    'epi_bd':'Bloody Diarrhea',
    'epi_ab':'Animal Bite',
    'epi_af':'Polio',
    'epi_mg':'Meningitis',
    'epi_me':'Measles',
    'epi_ch':'Cholera',
    'epi_gw':'Ginuea Worm',
    'epi_nt':'Neonatal Tetanus',
    'epi_yf':'Yellow Fever',
    'epi_pl':'Plague',
    'epi_ra':'Rabies',
    'epi_vf':'Hemorrhagic Fevers',
    'epi_ei':'Infectious Diseases',
    'birth':'Total',
    'death':'Total Child Deaths',
    'home':'Total Visits',
    'home_to':'Total Households Visited',
}


class CVSSubmissionColumn(XFormSubmissionColumn):
    def get_title(self):
        return self.title or (COLUMN_TITLE_DICT[self.keyword] if self.keyword in COLUMN_TITLE_DICT else '')


class CVSAttributeColumn(XFormAttributeColumn):
    def get_title(self):
        return self.title or (COLUMN_TITLE_DICT[self.keyword] if self.keyword in COLUMN_TITLE_DICT else '')


class ActiveReportersColumn(Column):
    def add_to_report(self, report, key, dictionary):
        val = active_reporters(report.start_date, report.end_date, report.location)
        reorganize_location(key, val, dictionary)

    def get_chart(self):
        from .views.chart import ActiveReportersChartView
        return ActiveReportersChartView(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date)

    def get_view_function(self):
        from .views.chart import ActiveReportersChartView
        return ActiveReportersChartView.as_view(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date)


class RegisteredReportersColumn(Column):
    def add_to_report(self, report, key, dictionary):
        val = registered_reporters(report.location)
        reorganize_location(key, val, dictionary)

    def get_chart(self):
        return None

    def get_view_function(self):
        return None


class MainReport(XFormReport):

    def get_top_columns(self):
        return [
            ('Malnutrition', '/cvs/muac/', 1),
            ('Epi', '/cvs/epi/', 3),
            ('Birth', '/cvs/birth/', 1),
            ('Death', '/cvs/death/', 1),
            ('Home', '/cvs/home/', 1),
            ('Reporters', '/cvs/reporter/', 2),
        ]

    muac = CVSSubmissionColumn('muac', title='Total New Cases', order=0, chart_title='Variation of Malnutrition Cases')
    ma = CVSAttributeColumn('epi_ma', order=1)
    tb = CVSAttributeColumn('epi_tb', order=2)
    bd = CVSAttributeColumn('epi_bd', order=3)
    birth = CVSSubmissionColumn('birth', order=4)
    death = CVSSubmissionColumn('death', order=5)
    home = CVSSubmissionColumn('home', order=6)
    reporters = RegisteredReportersColumn(order=7, title="Registered")
    active_reporters = ActiveReportersColumn(order=8, title="Active", chart_title='Active Reporters')

class MuacReport(XFormReport):
    total = CVSSubmissionColumn('muac', order=0, title='Total')
    green = CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_category':'G',
            }, order=1, title='Green')
    green_oe = CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_category':'G',
                'eav__muac_ignored':'T',
            }, order=2, title='Green+oe')

    yellow = CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_category':'Y',
            }, order=3, title='Yellow')
    red = CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_category':'R',
            }, order=4, title='Red')
    red_oe = CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_category':'R',
                'eav__muac_ignored':'T',
            }, order=5, title='Red+oe')


class EpiReport(XFormReport):
    total = CVSSubmissionColumn('epi', order=0, title='Total', chart_title='Variation of Total EPI Reports')
    bd = CVSAttributeColumn('epi_bd', order=1)
    ma = CVSAttributeColumn('epi_ma', order=2)
    tb = CVSAttributeColumn('epi_tb', order=3)
    ab = CVSAttributeColumn('epi_ab', order=4)
    af = CVSAttributeColumn('epi_af', order=5)
    mg = CVSAttributeColumn('epi_mg', order=6)
    me = CVSAttributeColumn('epi_me', order=7)
    ch = CVSAttributeColumn('epi_ch', order=8)
    gw = CVSAttributeColumn('epi_gw', order=9)
    nt = CVSAttributeColumn('epi_nt', order=10)
    yf = CVSAttributeColumn('epi_yf', order=11)
    pl = CVSAttributeColumn('epi_pl', order=12)
    ra = CVSAttributeColumn('epi_ra', order=13)
    vf = CVSAttributeColumn('epi_vf', order=14)
    ei = CVSAttributeColumn('epi_ei', order=15)


class BirthReport(XFormReport):
    at_home_filter = {'eav__birth_place':'HOME', }
    at_facility_filter = {'eav__birth_place':'FACILITY', }

    total = CVSSubmissionColumn('birth', order=0, title='Total Births')
    boys = CVSSubmissionColumn('birth', extra_filters={
                'eav__birth_gender':'M',
            }, order=1, title='Boys')
    girls = CVSSubmissionColumn('birth', extra_filters={
                'eav__birth_gender':'F',
            }, order=2, title='Girls')
    home = CVSSubmissionColumn('birth', extra_filters=at_home_filter, order=3, \
                               title='Delivered at Home')
    facility = CVSSubmissionColumn('birth', extra_filters=at_facility_filter, \
                                   order=4, title='Delivered at Facility')
    percent_home = QuotientColumn(\
        CVSSubmissionColumn('birth', extra_filters=at_home_filter), \
        CVSSubmissionColumn('birth'), \
        order=5, title='% Delivered at Home'
    )
    percent_facility = QuotientColumn(\
        CVSSubmissionColumn('birth', extra_filters=at_facility_filter), \
        CVSSubmissionColumn('birth'), \
        order=6, title='% Delivered at Facility'
    )



class DeathReport(XFormReport):
    total = CVSSubmissionColumn('death', order=0, title='Total Child Deaths')
    boys = CVSSubmissionColumn('death', order=1, extra_filters={
                'eav__death_gender':'M',
            }, title='Male Deaths')
    girls = CVSSubmissionColumn('death', order=2, extra_filters={
                'eav__death_gender':'F',
            }, title='Female Deaths')
    under_28days = CVSSubmissionColumn('death', order=3, extra_filters={
                'eav__death_age__lt':28,
            }, title='Deaths Under 1 month')
    upto_3months = CVSSubmissionColumn('death', order=4, extra_filters={
                'eav__death_age__range':(28, 90)
            }, title='Deaths 1 to 3 months')
    upto_12months = CVSSubmissionColumn('death', order=5, extra_filters={
                'eav__death_age__range':(90, 365)
            }, title='Deaths 3 months to 1 year')
    upto_5years = CVSSubmissionColumn('death', order=6, extra_filters={
                'eav__death_age__range':(365, 1825)
            }, title='Deaths 1 to 5 years')


class HomeReport(XFormReport):
    def get_top_columns(self):
        return [
            ('', '#', 2),
            ('Safe Drinking Water', '#', 2),
            ('Hand Washing Facilities', '#', 2),
            ('Latrines', '#', 2),
            ('ITTNs/LLINs', '#', 2),
        ]

    total = CVSSubmissionColumn('home', order=0, title='Total Reports')
    to = CVSAttributeColumn('home_to', order=1)
    wa = CVSAttributeColumn('home_wa', order=2, title='Total')
    wa_percent = QuotientColumn(\
        CVSAttributeColumn('home_wa'), \
        CVSAttributeColumn('home_to'), \
        order=3, title='% of Total',
        chart_title='Variation of % Safe Drinking Water',
    )
    ha = CVSAttributeColumn('home_ha', order=4, title='Total')
    ha_percent = QuotientColumn(\
        CVSAttributeColumn('home_ha'), \
        CVSAttributeColumn('home_to'), \
        order=5, title='% of Total',
        chart_title='Variation of % Hand Washing Facilities',
    )
    la = CVSAttributeColumn('home_la', order=6, title='Total')
    la_percent = QuotientColumn(\
        CVSAttributeColumn('home_la'), \
        CVSAttributeColumn('home_to'), \
        order=7, title='% of Total',
        chart_title='Variation of % Access to Latrines',
    )
    it = CVSAttributeColumn('home_it', order=8, title='Total')
    it_percent = QuotientColumn(\
        CVSAttributeColumn('home_it'), \
        CVSAttributeColumn('home_to'), \
        order=9, title='% of Total',
        chart_title='Variation of % Access to ITTNs/LLINs',
    )


