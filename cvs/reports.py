from generic.reporting.views import ReportView
from generic.reporting.reports import Column
from uganda_common.reports import XFormAttributeColumn, XFormSubmissionColumn, QuotientColumn, AdditionColumn, DifferenceColumn
from uganda_common.views import XFormReport
from .utils import active_reporters, registered_reporters, total_facility_submissions, total_facility_attributes, active_facility_reporters, registered_facility_reporters
from uganda_common.utils import reorganize_location
from cvs.views.reports import CVSReportView

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


def reorganize_hc(key, report, report_dict, facility_base='connection__contact__healthproviderbase__healthprovider__facility'):
    # getting to facility is a huge join, and these parameters and keys
    # get cumbersome
    id_key = "%s__id" % facility_base
    name_key = "%s__name" % facility_base
    type_key = "%s__type__name" % facility_base

    for rdict in report:
        location = rdict[id_key]
        report_dict.setdefault(location,
                {'location_name': "%s (%s)" % \
                 (rdict[name_key], rdict[type_key])})
        report_dict[location][key] = rdict['value']

class CVSSubmissionColumn(XFormSubmissionColumn):

    def get_title(self):
        return self.title or (COLUMN_TITLE_DICT[self.keyword] if self.keyword in COLUMN_TITLE_DICT else '')

    def add_to_report(self, report, key, dictionary):
        if report.drill_to_facility:
            val = total_facility_submissions(self.keyword, report.start_date, report.end_date, report.location, self.extra_filters)
            reorganize_hc(key, val, dictionary)
        else:
            XFormSubmissionColumn.add_to_report(self, report, key, dictionary)


class CVSAttributeColumn(XFormAttributeColumn):

    def get_title(self):
        tolookup = self.keyword
        if type(self.keyword) == list:
            tolookup = self.keyword[0]
        return self.title or (COLUMN_TITLE_DICT[tolookup] if tolookup in COLUMN_TITLE_DICT else '')

    def add_to_report(self, report, key, dictionary):
        if report.drill_to_facility:
            val = total_facility_attributes(self.keyword, report.start_date, report.end_date, report.location, self.extra_filters)
            reorganize_hc(key, val, dictionary, facility_base='submission__connection__contact__healthproviderbase__healthprovider__facility')
        else:
            XFormAttributeColumn.add_to_report(self, report, key, dictionary)


class ActiveReportersColumn(Column):
    def __init__(self, roles=['VHT', 'PVHT'], period=1, **kwargs):
        Column.__init__(self, **kwargs)
        self.roles = roles
        self.period = period

    def add_to_report(self, report, key, dictionary):
        if report.drill_to_facility:
            val = active_facility_reporters(report.start_date, report.end_date, report.location, roles=self.roles, period=self.period)
            reorganize_hc(key, val, dictionary)
        else:
            val = active_reporters(report.start_date, report.end_date, report.location, roles=self.roles, period=self.period)
            reorganize_location(key, val, dictionary)

    def get_chart(self):
        from .views.chart import ActiveReportersChartView
        return ActiveReportersChartView(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date, \
                         roles=self.roles, \
                         period=self.period)

    def get_view_function(self):
        from .views.chart import ActiveReportersChartView
        return ActiveReportersChartView.as_view(location_id=self.report.location.pk, \
                         start_date=self.report.start_date, \
                         end_date=self.report.end_date, \
                         roles=self.roles, \
                         period=self.period)


class RegisteredReportersColumn(Column):
    def __init__(self, roles=['VHT', 'PVHT'], **kwargs):
        Column.__init__(self, **kwargs)
        self.roles = roles

    def add_to_report(self, report, key, dictionary):
        if report.drill_to_facility:
            val = registered_facility_reporters(report.location, roles=self.roles)
            if 'HC' in self.roles:
                # add all health facilities, so we can show unregistered ones too
                from healthmodels.models import HealthFacility
                locations = report.location.get_descendants(include_self=True)
                for hc in HealthFacility.objects.filter(catchment_areas__in=locations):
                    dictionary.setdefault(hc.id, \
                            {'location_name': "%s (%s)" % \
                             (hc.name, hc.type.name)})
            reorganize_hc(key, val, dictionary, facility_base='facility')
        else:
            val = registered_reporters(report.location, roles=self.roles)
            reorganize_location(key, val, dictionary)

    def get_chart(self):
        return None

    def get_view_function(self):
        return None


class MainReport(CVSReportView):

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
    ma = CVSAttributeColumn(['epi_ma', 'com_fever'], order=1)
    tb = CVSAttributeColumn('epi_tb', order=2)
    bd = CVSAttributeColumn(['epi_bd', 'com_diarrhea'], order=3)
    birth = CVSSubmissionColumn('birth', order=4)
    death = CVSSubmissionColumn('death', order=5)
    home = CVSSubmissionColumn('home', order=6)
    reporters = RegisteredReportersColumn(order=7, title="Registered")
    active_reporters = ActiveReportersColumn(order=8, title="Active", chart_title='Active Reporters')

class MuacReport(CVSReportView):
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


class EpiReport(CVSReportView):
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


class BirthReport(CVSReportView):
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



class DeathReport(CVSReportView):
    total = CVSSubmissionColumn('olddeath', order=0, title='Total Child Deaths')
    boys = CVSSubmissionColumn('olddeath', order=1, extra_filters={
                'eav__olddeath_gender':'M',
            }, title='Male Deaths')
    girls = CVSSubmissionColumn('olddeath', order=2, extra_filters={
                'eav__olddeath_gender':'F',
            }, title='Female Deaths')
    under_28days = CVSSubmissionColumn('olddeath', order=3, extra_filters={
                'eav__olddeath_age__lt':28,
            }, title='Deaths Under 1 month')
    upto_3months = CVSSubmissionColumn('olddeath', order=4, extra_filters={
                'eav__olddeath_age__range':(28, 90)
            }, title='Deaths 1 to 3 months')
    upto_12months = CVSSubmissionColumn('olddeath', order=5, extra_filters={
                'eav__olddeath_age__range':(90, 365)
            }, title='Deaths 3 months to 1 year')
    upto_5years = CVSSubmissionColumn('olddeath', order=6, extra_filters={
                'eav__olddeath_age__range':(365, 1825)
            }, title='Deaths 1 to 5 years')


class HomeReport(CVSReportView):
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

class MTrackReport(CVSReportView):
    template_name = "cvs/partials/stats_base.html"

    def get_top_columns(self):
        return [
            ('Diseases', '/mtrack/epi/', 4),
            ('OPD/IPD', '/mtrack/birth/', 3),
            ('Nutrition', '/mtrack/muac/', 2),
            ('Active Reporters', '/cvs/reporter/', 1),
        ]

    ma_hc = CVSAttributeColumn('cases_ma', order=1, title='Malaria (HC)')
    ma_vht = CVSAttributeColumn(['epi_ma', 'com_fever'], order=2, title='Fever (VHT)')
    bd_hc = CVSAttributeColumn('cases_bd', order=3, title='Dysentery (HC)')
    bd_vht = CVSAttributeColumn(['epi_bd', 'com_diarrhea'], order=4, title='Diarrhea (VHT)')
    opd_att = CVSAttributeColumn('opd_att', order=5, title='New Attendance')
    opd_md = CVSAttributeColumn('opd_md', order=6, title='Maternal Death')
    opd_pd = CVSAttributeColumn('opd_pd', order=7, title='Perinatal Death')
    com_muac_red = AdditionColumn(\
            CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_category':'R',
            }),
            CVSAttributeColumn('com_muac_red'), \
            order=8, title='Total Red (VHT)')

    opd_nat = CVSAttributeColumn('opd_nat', order=9, title='New Attendees (HC)')
    active_reporters = ActiveReportersColumn(order=10, title="Submitted Report For Last Period", chart_title='Active Reporters')

    def get_default_column(self):
        return ('ma_vht', self.ma_vht)

class MTrackEpiReport(CVSReportView):
    def get_top_columns(self):
        return [
            ('VHTs', '#', 4),
            ('Malaria', '/mtrack/malaria/', 1),
            ('Health Center', '#', 3),
        ]

#    ma_vht = CVSAttributeColumn(['epi_ma', 'com_fever'], order=1, title='Malaria')
#FIXME charts should take multi values
    ma_vht = CVSAttributeColumn('com_fever', order=1, title='Fever')
    tb_vht = CVSAttributeColumn('epi_tb', order=2, title='Tb')
    pneumonia = CVSAttributeColumn('com_pneumonia', order=3, title='Fast Breathing')
    bd_vht = CVSAttributeColumn(['epi_bd', 'com_diarrhea'], order=4, title='Diarrhea')

    ma_hc = CVSAttributeColumn('cases_ma', order=5, title='Malaria (HC)')
    dy_hc = CVSAttributeColumn('cases_dy', order=6, title='Dysentery (HC)')
    sa_hc = CVSAttributeColumn('cases_sa', order=7, title='SARI (fast breathing)')
    ab_hc = CVSAttributeColumn('cases_ab', order=8, title='Animal Bites')

class MTrackBirthReport(CVSReportView):
    at_home_filter = {'eav__birth_place':'HOME', }
    at_facility_filter = {'eav__birth_place':'FACILITY', }

    def get_top_columns(self):
        return [
            ('VHTs', '#', 3),
            ('Health Center', '#', 4),
        ]

    total = CVSSubmissionColumn('birth', order=0, title='Total Births')
    percent_home = QuotientColumn(\
        CVSSubmissionColumn('birth', extra_filters=at_home_filter), \
        CVSSubmissionColumn('birth'), \
        order=1, title='% Delivered at Home'
    )
    deaths_total = CVSAttributeColumn('com_death', order=2, title='Total Deaths')
    opd_att = CVSAttributeColumn('opd_att', order=3, title='New Attendance')
    opd_nat = CVSAttributeColumn('opd_nat', order=4, title='Total Attendance')
    opd_md = CVSAttributeColumn('opd_md', order=5, title='Maternal Death')
    opd_pd = CVSAttributeColumn('opd_pd', order=6, title='Perinatal Death')

class MTrackNutritionReport(CVSReportView):

    def get_top_columns(self):
        return [
            ('VHTs', '#', 4),
            ('Health Center', '#', 4),
        ]

    red = AdditionColumn(\
            CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_category':'R',
            }),
            CVSAttributeColumn('com_muac_red'), \
            order=1, title='Red')

    yellow = AdditionColumn(\
            CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_category':'Y',
            }),
            CVSAttributeColumn('com_muac_yellow'), \
            order=2, title='Yellow')

    green = AdditionColumn(\
            CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_category':'G',
            }),
            CVSAttributeColumn('com_muac_green'), \
            order=3, title='Green')

    oe = AdditionColumn(\
            CVSSubmissionColumn('muac', extra_filters={
                'eav__muac_ignored':'T',
            }),
            CVSAttributeColumn('com_bi_od'), \
            order=4, title='Oedema')

    new_adm = CVSAttributeColumn('mal_total_new', order=5, title='New Admissions')
    tot_adm = CVSAttributeColumn('mal_total_admissions', order=6, title='Total Admissions')
    defaults = CVSAttributeColumn('mal_total_default', order=7, title='Defaults')
    deaths = CVSAttributeColumn('mal_total_death', order=8, title='Deaths')


class MTrackMalariaReport(CVSReportView):

    def get_top_columns(self):
        return [
            ('Test', '#', 7),
            ('Treat', '#', 8)
        ]

    test_sm = CVSAttributeColumn('test_sm', order=0, title='Suspected Malaria Cases')
    test_rdt = CVSAttributeColumn('test_rdt', order=1, title='RDT tested cases')
    test_rdp = CVSAttributeColumn('test_rdp', order=2, title='RDT positive cases')
    test_mtc = CVSAttributeColumn('test_mtc', order=3, title='Microscopy tested cases')
    test_mtp = CVSAttributeColumn('test_mtp', order=4, title='Microscopy positive cases')
    test_pcc = CVSAttributeColumn('test_pcc', order=5, title='Positive cases under 5 years')
    test_pcy = CVSAttributeColumn('test_pcy', order=6, title='Positive cases 5+ years')
    treat_rdn = CVSAttributeColumn('treat_rdn', order=7, title='RDT negative cases treated')
    treat_rdp = CVSAttributeColumn('treat_rdp', order=8, title='RDT positive cases treated')
    treat_mtn = CVSAttributeColumn('treat_mtn', order=9, title='Microscopy negative cases treated')
    treat_mtp = CVSAttributeColumn('treat_mtp', order=10, title='Microscopy positive cases treated')
    treat_tin = CVSAttributeColumn('treat_tin', order=11, title='4+ months to 2 years')
    treat_tic = CVSAttributeColumn('treat_tic', order=12, title='3+ to 6 years')
    treat_tiy = CVSAttributeColumn('treat_tiy', order=13, title='7+ to 11 years')
    treat_tia = CVSAttributeColumn('treat_tia', order=14, title='12+ years')
