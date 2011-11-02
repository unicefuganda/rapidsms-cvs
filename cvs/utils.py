import itertools
from django.db import connection
from django.db.models import Q, Sum
from django.utils.datastructures import SortedDict
from django.contrib.auth.models import Group
from healthmodels.models.HealthProvider import HealthProvider, HealthProviderBase
from rapidsms_xforms.models import *
import datetime
import time
from django.http import HttpResponse
from django.db.models import Count
from uganda_common.utils import TIME_RANGES
from rapidsms_httprouter.models import Message
from contact.models import MassText
from poll.models import Poll, Category, Rule
from rapidsms.contrib.locations.models import Location
from django.conf import settings
from script.models import Script, ScriptStep
from rapidsms.models import Contact

try:
    from django.contrib.sites import Site
except ImportError:
    pass

XFORMS = [
    'epi', # Weekly-submitted VHT epidemiological reports
    'home', # Monthly-submitted PVHT home visitation reports
    'muac', # VHT report of child malnutrition
    'birth', # VHT report of a birth
    'death', # VHT report of a death
    'itp', # Health Center report of an inpatient treatment
    'otp', # Health Center report of an outpatient treatment
    'cure', # Health Center report of patient cure
    'reg', # Registers a reporter with their name
    'pvht', # Registers a PVHT with their facility
    'vht', # Registers a VHT with their facility
    'com', # Routine VHT Report of weekly aggregate indicators
    'mal', # Routine HC report of weekly itp/otp treatments
    'rutf', # Routine HC report of weekly otc/itc stock reports
    'act', # Routine report of ACT stock
]

GROUP_BY_WEEK = 1
GROUP_BY_MONTH = 2
GROUP_BY_DAY = 16
GROUP_BY_QUARTER = 32

GROUP_BY_SELECTS = {
    GROUP_BY_DAY:('day', 'date(rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_WEEK:('week', 'extract(week from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_MONTH:('month', 'extract(month from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_QUARTER:('quarter', 'extract(quarter from rapidsms_xforms_xformsubmission.created)',),
}


def active_reporters(start_date, end_date, location, group_by_timespan=None):
    """ get all active reporters  """

    tnum = 5
    select = {
        'location_name':'T%d.name' % tnum,
        'location_id':'T%d.id' % tnum,
        'rght':'T%d.rght' % tnum,
        'lft':'T%d.lft' % tnum
    }

    values = ['location_name', 'location_id', 'lft', 'rght']
    if group_by_timespan:
         select_value = GROUP_BY_SELECTS[group_by_timespan][0]
         select_clause = GROUP_BY_SELECTS[group_by_timespan][1]
         select.update({select_value:select_clause,
                        'year':'extract (year from rapidsms_xforms_xformsubmission.created)', })
         values.extend([select_value, 'year'])
    if location.get_children().count() > 1:
        location_children_where = 'T%d.id in %s' % (tnum, (str(tuple(location.get_children().values_list(\
                       'pk', flat=True)))))
    else:
        location_children_where = 'T%d.id = %d' % (tnum, location.get_children()[0].pk)
    return XFormSubmission.objects.filter(
               has_errors=False,
               created__lte=end_date,
               created__gte=start_date).values(
               'connection__contact__reporting_location__name').extra(
               tables=['locations_location'],
               where=[\
                   'T%d.lft <= locations_location.lft' % tnum, \
                   'T%d.rght >= locations_location.rght' % tnum, \
                   location_children_where]).extra(\
               select=select).values(*values).annotate(value=Count('connection__id')).extra(order_by=['location_name'])

def registered_reporters(location):
    tnum = 6
    select = {
        'location_name':'T%d.name' % tnum,
        'location_id':'T%d.id' % tnum,
        'rght':'T%d.rght' % tnum,
        'lft':'T%d.lft' % tnum,
    }
    values = ['location_name', 'location_id', 'rght', 'lft']
    if location.get_children().count() > 1:
        location_children_where = 'T%d.id in %s' % (tnum, (str(tuple(location.get_children().values_list(\
                       'pk', flat=True)))))
    else:
        location_children_where = 'T%d.id = %d' % (tnum, location.get_children()[0].pk)
    return  HealthProviderBase.objects.filter(groups=Group.objects.get(name='VHT')).values('location__name').extra(
            tables=['locations_location'], where=[\
                   'T%d.lft <= locations_location.lft' % tnum, \
                   'T%d.rght >= locations_location.rght' % tnum, \
                   location_children_where]).extra(select=select).values(*values).annotate(value=Count('id'))

def total_submissions_by_facility(keyword, start_date, end_date, map_window):
    minlat, minlon, maxlat, maxlon = map_window
    return XFormSubmission.objects.filter(**{
        'has_errors':False,
        'xform__keyword':keyword,
        'has_errors':False,
        'created__lte':end_date,
        'created__gte':start_date,
        'connection__contact__healthproviderbase__facility__location__latitude__range':(str(minlat), str(maxlat),),
        'connection__contact__healthproviderbase__facility__location__longitude__range':(str(minlon), str(maxlon),)})\
        .extra(
        tables=['healthmodels_healthfacilitytypebase'],
        where=['healthmodels_healthfacilitybase.type_id=healthmodels_healthfacilitytypebase.id'])\
        .extra(select={
        'facility_name':'healthmodels_healthfacilitybase.name',
        'facility_id':'healthmodels_healthfacilitybase.id',
        'latitude':'locations_point.latitude',
        'longitude':'locations_point.longitude',
        'type':'healthmodels_healthfacilitytypebase.name'})\
        .values('facility_name', 'facility_id', 'latitude', 'longitude', 'type')\
        .annotate(value=Count('id'))

def total_attribute_by_facility(attribute_slug, start_date, end_date, map_window):
    minlat, minlon, maxlat, maxlon = map_window
    return XFormSubmissionValue.objects.filter(**{
               'submission__has_errors':False,
               'attribute__slug':attribute_slug,
               'submission__created__lte':end_date,
               'submission__created__gte':start_date,
               'submission__connection__contact__healthproviderbase__facility__location__latitude__range':(str(minlat), str(maxlat),),
               'submission__connection__contact__healthproviderbase__facility__location__longitude__range':(str(minlon), str(maxlon),)})\
        .extra(
        tables=['healthmodels_healthfacilitytypebase'],
        where=['healthmodels_healthfacilitybase.type_id=healthmodels_healthfacilitytypebase.id'])\
        .extra(select={
        'facility_name':'healthmodels_healthfacilitybase.name',
        'facility_id':'healthmodels_healthfacilitybase.id',
        'latitude':'locations_point.latitude',
        'longitude':'locations_point.longitude',
        'type':'healthmodels_healthfacilitytypebase.name'})\
        .values('facility_name', 'facility_id', 'latitude', 'longitude', 'type')\
        .annotate(value=Sum('value_int'))

def get_area(request):
    if request.user.is_authenticated() and Location.objects.filter(type__name='district', name=request.user.username).count():
        area = Location.objects.filter(type__name='district', name=request.user.username)[0]
    elif request.user.is_authenticated() and Contact.objects.filter(user=request.user).count():
        area = Contact.objects.filter(user=request.user)[0].reporting_location
    else:
        area = Location.tree.root_nodes()[0]
    return area

def get_reporters(**kwargs):
    request = kwargs.pop('request')
    area = get_area(request)
    if area:
        return HealthProvider.objects.filter(reporting_location__in=area.get_descendants(include_self=True).all()).select_related('facility', 'location').annotate(Count('connection__submissions')).all()
    else:
        return HealthProvider.objects.select_related('facility', 'location').annotate(Count('connection__submissions')).all()

def get_messages(**kwargs):
    request = kwargs.pop('request')
    area = get_area(request)
    if area:
        return Message.objects.filter(direction='I', connection__contact__reporting_location__in=area.get_descendants(include_self=True).all())

    return Message.objects.filter(direction='I')

def get_mass_messages(**kwargs):
    request = kwargs.pop('request')
    if request.user.is_authenticated():
        return [(p.question, p.start_date, p.user.username, p.contacts.count(), 'Poll Message') for p in Poll.objects.filter(user=request.user).exclude(start_date=None)] + [(m.text, m.date, m.user.username, m.contacts.count(), 'Mass Text') for m in MassText.objects.filter(user=request.user)]
    return [(p.question, p.start_date, p.user.username, p.contacts.count(), 'Poll Message') for p in Poll.objects.exclude(start_date=None)] + [(m.text, m.date, m.user.username, m.contacts.count(), 'Mass Text') for m in MassText.objects.all()]

class ExcelResponse(HttpResponse):
    def __init__(self, data, output_name='excel_report', headers=None, force_csv=False, encoding='utf8'):
        # Make sure we've got the right type of data to work with
        valid_data = False
        if hasattr(data, '__getitem__'):
            if isinstance(data[0], dict):
                if headers is None:
                    headers = data[0].keys()
                data = [[row[col] for col in headers] for row in data]
                data.insert(0, headers)
            if hasattr(data[0], '__getitem__'):
                valid_data = True
        import StringIO
        output = StringIO.StringIO()
        # Excel has a limit on number of rows; if we have more than that, make a csv
        use_xls = False
        if len(data) <= 65536 and force_csv is not True:
            try:
                import xlwt
            except ImportError:
                # xlwt doesn't exist; fall back to csv
                pass
            else:
                use_xls = True
        if use_xls:
            ##formatting of the cells
            # Grey background for the header row
            BkgPat = xlwt.Pattern()
            BkgPat.pattern = xlwt.Pattern.SOLID_PATTERN
            BkgPat.pattern_fore_colour = 22

            # Bold Fonts for the header row
            font = xlwt.Font()
            font.name = 'Calibri'
            font.bold = True

            # Non-Bold fonts for the body
            font0 = xlwt.Font()
            font0.name = 'Calibri'
            font0.bold = False

            # style and write field labels
            style = xlwt.XFStyle()
            style.font = font
            style.pattern = BkgPat

            style0 = xlwt.XFStyle()
            style0.font = font0
            book = xlwt.Workbook(encoding=encoding)
            sheet = book.add_sheet('Sheet 1')
            styles = {'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
                      'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
                      'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
                      'default': style0,
                      'header':style}

            for rowx, row in enumerate(data):
                for colx, value in enumerate(row):
                    if isinstance(value, datetime.datetime):
                        cell_style = styles['datetime']
                    elif isinstance(value, datetime.date):
                        cell_style = styles['date']
                    elif isinstance(value, datetime.time):
                        cell_style = styles['time']
                    elif rowx == 0:
                        cell_style = styles['header']
                    else:
                        cell_style = styles['default']

                    sheet.write(rowx, colx, value, style=cell_style)
            book.save(output)
            mimetype = 'application/vnd.ms-excel'
            file_ext = 'xls'
        else:
            for row in data:
                out_row = []
                for value in row:
                    if not isinstance(value, basestring):
                        value = unicode(value)
                    value = value.encode(encoding)
                    out_row.append(value.replace('"', '""'))
                output.write('"%s"\n' %
                             '","'.join(out_row))
            mimetype = 'text/csv'
            file_ext = 'csv'
        output.seek(0)
        super(ExcelResponse, self).__init__(content=output.getvalue(),
                                            mimetype=mimetype)
        self['Content-Disposition'] = 'attachment;filename="%s.%s"' % \
            (output_name.replace('"', '\"'), file_ext)

def monthly_reports():
    for contact in Contact.objects.filter(groups__name__in=['VHT', 'PVHT', 'HC']):
        if len(set(contact.groups.all().values_list('name', flat=True)) & set(['OTC', 'ITC'])) > 0:
            reports = XFormSubmission.objects.filter(\
                        connection__contact=contact, \
                        has_errors=False, \
                        xform__keyword__iexact='mal', \
                        created__gte=datetime.datetime.now() - datetime.timedelta(days=30)
                        ).count()
        else:
            reports = XFormSubmission.objects.filter(\
                        connection__contact=contact, \
                        has_errors=False, \
                        xform__keyword__iexact='com', \
                        created__gte=datetime.datetime.now() - datetime.timedelta(days=30)
                        ).count()

        msg = 'Last month you submitted %s timely reports in 4 weeks:' % reports

        if reports >= 4:
            msg = msg + ' You are one of our best reporters! Thank you for serving your community.'
        elif reports == 3:
            msg = msg + ' Thanks for your good work. Please remember to send your reports.'
        elif reports == 2:
            msg = msg + ' Thanks for your effort. Please remember to submit on time.'
        else:
            msg = msg + ' Your reports are important. Please make an effort to submit on time.'

        Message.objects.create(connection=contact.default_connection,
                                     text=msg,
                                     direction='O',
                                     status='P')

def get_training_messages(request):
    return Message.objects.filter(connection__contact__active=False)

def get_training_vhts(request):
    return HealthProvider.objects.filter(active=False)

def get_nolocation_vhts(request):
    return HealthProvider.objects.filter(location=None, reporting_location=None)

def get_dashboard_messages(request=None):
    # FIXME: implement full functionality
    return Message.objects.filter(direction='I')

