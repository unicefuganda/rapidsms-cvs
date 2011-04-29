from cvs.forms import DateRangeForm
from django.db import connection
from django.db.models import Q, Sum
from django.utils.datastructures import SortedDict
from cvs.forms import DateRangeForm
from django.contrib.auth.models import Group
from healthmodels.models.HealthProvider import HealthProvider, HealthProviderBase
from math import floor
from rapidsms_xforms.models import *
import datetime
from django.http import HttpResponse
from django.db.models import Count
from uganda_common.utils import TIME_RANGES

def init_xforms():
    DISEASE_CHOICES = [
        ('bd','int','Bloody diarrhea (Dysentery)', False),
        ('ma','int','Malaria', False),
        ('tb','int','Tuberculosis', False),
        ('ab','int','Animal Bites', False),
        ('af','int','Acute Flaccid Paralysis (Polio)', False),
        ('mg','int','Meningitis', False),
        ('me','int','Measles', False),
        ('ch','int','Cholera', False),
        ('gw','int','Guinea Worm', False),
        ('nt','int','Neonatal Tetanus', False),
        ('yf','int','Yellow Fever', False),
        ('pl','int','Plague', False),
        ('ra','int','Rabies', False),
        ('vf','int','Other Viral Hemorrhagic Fevers', False),
        ('ei','int','Other Emerging Infectious Diseases', False),
    ]

    HOME_ATTRIBUTES = [
       ('to','int','Total Homesteads Visited', False),
       ('it','int','ITTNs/LLINs', False),
       ('la','int','Latrines', False),
       ('ha','int','Handwashing Facilities', False),
       ('wa','int','Safe Drinking Water', False),
    ]

    XFORMS = (
        ('epi','Epi Report','Weekly-submitted VHT epidemiological reports'),
        ('home','Home Report','Monthly-submitted PVHT home visitation reports'),
        ('muac','Malnu Report','VHT report of child malnutrition'),
        ('birth','Birth Report','VHT report of a birth'),
        ('death','Death Report','VHT report of a death'),
        ('itp','Inpatient Treatment Report','Health Center report of an inpatient treatment',),
        ('otp','Outpatient Treatment Report','Health Center report of an outpatient treatment',),
        ('cure','Cure Treatment Report','Health Center report of patient cure',),
        ('reg','Registration','Registers a reporter with their name',),
        ('pvht','PVHT Signup','Registers a PVHT with their facility',),
        ('vht','VHT Signup','Registers a VHT with their facility',),
    )

    XFORM_FIELDS = {
        'muac':[
             ('name', 'text', 'The name of the malnourished patient', True),
             ('gender', 'cvssex','The gender of the malnourished patient', True),
             ('age', 'cvstdelt', 'The age of the malnurished patient', True),
             ('category','cvsmuacr', 'Red, yellow, or green case of malnutrition', True),
             ('ignored','cvsodema', 'Occurence of oedema (T/F)', False)
         ],
        'birth':[
             ('name', 'text', 'The name of the child born', True),
             ('gender', 'cvssex', 'The gender of the child born', True),
             ('place','cvsloc', 'At home or at a health facility', True),
         ],
         'death':[
             ('name','text','The name of the person who has died', True),
             ('gender', 'cvssex', 'The gender of the person who has died', True),
             ('age', 'cvstdelt', 'The age of the person who has died', True),
         ],
        'epi':DISEASE_CHOICES,
        'home':HOME_ATTRIBUTES,
        'reg':[
             ('name','text','Your name', True),
        ],
        'vht':[
             ('facility','facility','Your facility code', True),
        ],
        'pvht':[
             ('facility','facility','Your facility code', True),
        ],
    }

    user = User.objects.get(username='admin')
    xform_dict = {}
    for tuple in XFORMS:
        xform, created = XForm.objects.get_or_create(
            keyword=tuple[0],
            defaults={
                'name':tuple[1],
                'description':tuple[2],
                'response':'',
                'active':True,
                'owner':user,
                'site':Site.objects.get_current(),
                'separator':',',
                'command_prefix':'',
                'keyword_prefix':'+',
            }
        )
        xform_dict[tuple[0]] = xform

    for form_key, attributes in XFORM_FIELDS.items():
        order = 0
        form = xform_dict[form_key]
        for attribute in attributes:
            xformfield, created = XFormField.objects.get_or_create(
                command = attribute[0],
                xform=form,
                defaults={
                    'order':order,
                    'field_type':attribute[1],
                    'type':attribute[1],
                    'name':attribute[2],
                    'description':attribute[2],
                }
            )
            if attribute[3]:
                xformfieldconstraint, created = XFormFieldConstraint.objects.get_or_create(
                    field=xformfield,
                    defaults={
                        'type':'req_val',
                         'message':("Expected %s, none provided." % attribute[2])
                    }
            )
            order = order + 1
    return xform_dict


GROUP_BY_WEEK = 1
GROUP_BY_MONTH = 2
GROUP_BY_DAY = 16
GROUP_BY_QUARTER = 32

months={
    1: 'Jan',
    2: 'Feb',
    3: 'Mar',
    4: 'Apr',
    5: 'May',
    6: 'Jun',
    7: 'Jul',
    8: 'Aug',
    9: 'Sept',
    10: 'Oct',
    11: 'Nov',
    12: 'Dec'
}

quarters = {
    1:'First',
    2:'Second',
    3:'Third',
    4:'Forth'
}

GROUP_BY_SELECTS = {
    GROUP_BY_DAY:('day','date(rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_WEEK:('week','extract(week from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_MONTH:('month','extract(month from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_QUARTER:('quarter','extract(quarter from rapidsms_xforms_xformsubmission.created)',),
}

def total_submissions(keyword, start_date, end_date, location, extra_filters=None, group_by_timespan=None):
    if extra_filters:
        q = XFormSubmission.objects.filter(**extra_filters)
        tnum = 8
    else:
        q = XFormSubmission.objects
        tnum = 6
    select = {
        'location_name':'T%d.name' % tnum,
        'location_id':'T%d.id' % tnum,
        'rght':'T%d.rght' % tnum,
        'lft':'T%d.lft' % tnum
    }
    values = ['location_name','location_id','lft','rght']
    if group_by_timespan:
         select_value = GROUP_BY_SELECTS[group_by_timespan][0]
         select_clause = GROUP_BY_SELECTS[group_by_timespan][1]
         select.update({select_value:select_clause,
                        'year':'extract (year from rapidsms_xforms_xformsubmission.created)',})
         values.extend([select_value,'year'])
    if location.get_children().count() > 1:
        location_children_where = 'T%d.id in %s' % (tnum, (str(tuple(location.get_children().values_list(\
                       'pk', flat=True)))))
    else:
        location_children_where = 'T%d.id = %d' % (tnum, location.get_children()[0].pk)

    return q.filter(
               xform__keyword=keyword,
               has_errors=False,
               created__lte=end_date,
               created__gte=start_date).values(
               'connection__contact__reporting_location__name').extra(
               tables=['simple_locations_area'],
               where=[\
                   'T%d.lft <= simple_locations_area.lft' % tnum,\
                   'T%d.rght >= simple_locations_area.rght' % tnum,\
                   location_children_where]).extra(\
               select=select).values(*values).annotate(value=Count('id')).extra(order_by=['location_name'])

def total_submissions_by_facility(keyword, start_date, end_date, map_window):
    minlat, minlon, maxlat, maxlon = map_window
    return XFormSubmission.objects.filter(**{
        'has_errors':False,
        'xform__keyword':keyword,
        'has_errors':False,
        'created__lte':end_date,
        'created__gte':start_date,
        'connection__contact__healthproviderbase__facility__location__latitude__range':(str(minlat),str(maxlat),),
        'connection__contact__healthproviderbase__facility__location__longitude__range':(str(minlon),str(maxlon),)})\
        .extra(
        tables=['healthmodels_healthfacilitytypebase'],
        where=['healthmodels_healthfacilitybase.type_id=healthmodels_healthfacilitytypebase.id'])\
        .extra(select={
        'facility_name':'healthmodels_healthfacilitybase.name',
        'facility_id':'healthmodels_healthfacilitybase.id',
        'latitude':'simple_locations_point.latitude',
        'longitude':'simple_locations_point.longitude',
        'type':'healthmodels_healthfacilitytypebase.name'})\
        .values('facility_name','facility_id','latitude','longitude','type')\
        .annotate(value=Count('id'))

def total_attribute_value(attribute_slug, start_date, end_date, location, group_by_timespan=None):
    select = {
        'location_name':'T8.name',
        'location_id':'T8.id',
        'rght':'T8.rght',
        'lft':'T8.lft',
    }
    values = ['location_name','location_id','lft','rght']
    if group_by_timespan:
         select_value = GROUP_BY_SELECTS[group_by_timespan][0]
         select_clause = GROUP_BY_SELECTS[group_by_timespan][1]
         select.update({select_value:select_clause,
                        'year':'extract (year from rapidsms_xforms_xformsubmission.created)',})
         values.extend([select_value,'year'])
    if location.get_children().count() > 1:
        location_children_where = 'T8.id in %s' % (str(tuple(location.get_children().values_list(\
                       'pk', flat=True))))
    else:
        location_children_where = 'T8.id = %d' % location.get_children()[0].pk    
    return XFormSubmissionValue.objects.filter(
               submission__has_errors=False,
               attribute__slug=attribute_slug,
               submission__created__lte=end_date,
               submission__created__gte=start_date).values(
               'submission__connection__contact__reporting_location__name').extra(
               tables=['simple_locations_area'],
               where=[\
                   'T8.lft <= simple_locations_area.lft',
                   'T8.rght >= simple_locations_area.rght',
                   location_children_where]).extra(\
               select=select).values(*values).annotate(value=Sum('value_int')).extra(order_by=['location_name'])

def total_attribute_by_facility(attribute_slug, start_date, end_date, map_window):
    minlat, minlon, maxlat, maxlon = map_window
    return XFormSubmissionValue.objects.filter(**{
               'submission__has_errors':False,
               'attribute__slug':attribute_slug,
               'submission__created__lte':end_date,
               'submission__created__gte':start_date,
               'submission__connection__contact__healthproviderbase__facility__location__latitude__range':(str(minlat),str(maxlat),),
               'submission__connection__contact__healthproviderbase__facility__location__longitude__range':(str(minlon),str(maxlon),)})\
        .extra(
        tables=['healthmodels_healthfacilitytypebase'],
        where=['healthmodels_healthfacilitybase.type_id=healthmodels_healthfacilitytypebase.id'])\
        .extra(select={
        'facility_name':'healthmodels_healthfacilitybase.name',
        'facility_id':'healthmodels_healthfacilitybase.id',
        'latitude':'simple_locations_point.latitude',
        'longitude':'simple_locations_point.longitude',
        'type':'healthmodels_healthfacilitytypebase.name'})\
        .values('facility_name','facility_id','latitude','longitude','type')\
        .annotate(value=Sum('value_int'))

def reorganize_location(key, report, report_dict):
    for dict in report:
        location = dict['location_name']
        report_dict.setdefault(location,{'location_id':dict['location_id'],'diff':(dict['lft']-dict['rght'])})
        report_dict[location][key] = dict['value']

def reorganize_timespan(timespan, report, report_dict, location_list,request=None):
    for dict in report:
        time = dict[timespan]
        if timespan =='month':
            time = datetime.datetime(int(dict['year']), int(time), 1)
        elif timespan =='week':
            time = datetime.datetime(int(dict['year']), 1, 1) + datetime.timedelta(days = (int(time)*7))
        elif timespan =='quarter':
            time = datetime.datetime(int(dict['year']), int(time)*3, 1)

        report_dict.setdefault(time,{})
        location = dict['location_name']
        report_dict[time][location] = dict['value']

        if not location in location_list:
            location_list.append(location)
        
#def reorganize_timespan(timespan, report, report_dict, location_list,request=None):
#    for dict in report:
#        time = dict[timespan]
#        if timespan =='month':
#            time = months[int(time)]
#        elif timespan =='week':
#            time = 'Week '+str(int(time))
#        elif timespan =='quarter':
#            time = quarters[int(time)]+ ' Quarter'
#        else:
#            format = '%d-%m-%Y'
#            time = time.strftime(format)
#
#
#        report_dict.setdefault(time,{})
#        location = dict['location_name']
#        report_dict[time][location] = dict['value']
#
#        if not location in location_list:
#            location_list.append(location)

#@never_cache
def get_dates(request):
    """
    Process date variables from POST
    """
    if request.POST:
        form = DateRangeForm(request.POST)
        if form.is_valid():
            cursor = connection.cursor()
            cursor.execute("select min(created) from rapidsms_xforms_xformsubmission")
            min_date = cursor.fetchone()[0]
            start_date = form.cleaned_data['start_ts']
            end_date = form.cleaned_data['end_ts']
            request.session['start_date'] = start_date
            request.session['end_date'] = end_date
    elif request.GET.get('start_date',None) and request.GET.get('end_date',None):
        start_date=datetime.datetime.fromtimestamp(int(request.GET['start_date']))
        end_date=datetime.datetime.fromtimestamp(int(request.GET['end_date']))
        request.session['start_date'] = start_date
        request.session['end_date'] = end_date
        return {'start':start_date, 'end':end_date}
    else:
        form = DateRangeForm()
        cursor = connection.cursor()
        cursor.execute("select min(created), max(created) from rapidsms_xforms_xformsubmission")
        min_date, end_date = cursor.fetchone()
        start_date = end_date - datetime.timedelta(days=30)
        if request.GET.get('date_range',None):
            start_date,end_date=TIME_RANGES[request.GET.get('date_range')]()
            request.session['start_date'],request.session['end_date']=start_date,end_date
        if request.session.get('start_date',None)  and request.session.get('end_date',None):
            start_date=request.session['start_date']
            end_date=request.session['end_date']

    return {'start':start_date, 'end':end_date, 'min':min_date, 'form':form}

def get_expected_epi(location, request):
    dates = get_dates(request)
    health_providers = HealthProvider.objects.filter(location__in=location.get_descendants(),
                                                     groups=Group.objects.get(name='Village Health Team')).count()

    datediff = dates['end'] - dates['start']
    weeks = floor((datediff.days / 7))
    if weeks == 0:
        weeks = 1
    return health_providers * weeks

def get_group_by(start_date, end_date):
    interval=end_date-start_date
    if interval<=datetime.timedelta(days=21):
        group_by=GROUP_BY_DAY
        prefix = 'day'
    elif datetime.timedelta(days=21) <=interval<=datetime.timedelta(days=90):
        group_by=GROUP_BY_WEEK
        prefix = 'week'
    elif datetime.timedelta(days=90) <=interval<=datetime.timedelta(days=270):
        group_by=GROUP_BY_MONTH
        prefix = 'month'
    else:
        group_by=GROUP_BY_QUARTER
        prefix = 'quarter'
    return {'group_by':group_by, 'group_by_name':prefix}

def get_reporters():
#    return HealthProviderBase.objects.raw("select h.*, c.name, conn.identity, max(subs.created) as last_date, count(subs.id) as num_reports from healthmodels_healthproviderbase h join rapidsms_contact c on h.contact_ptr_id = c.id join rapidsms_connection conn on conn.contact_id = c.id join rapidsms_xforms_xformsubmission subs on subs.connection_id = conn.id group by h.contact_ptr_id, h.facility_id, h.location_id, c.name, conn.identity")
    return HealthProvider.objects.select_related('facility', 'location').annotate(Count('connection__submissions')).all()

class ExcelResponse(HttpResponse):
    def __init__(self,data, output_name='excel_report',headers=None,force_csv=False, encoding='utf8'):
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
                    elif rowx==0:
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

