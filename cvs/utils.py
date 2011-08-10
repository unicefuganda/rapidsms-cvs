import itertools
from django.db import connection
from django.db.models import Q, Sum
from django.utils.datastructures import SortedDict
from django.contrib.auth.models import Group
from healthmodels.models.HealthProvider import HealthProvider, HealthProviderBase
from rapidsms_xforms.models import *
import datetime
from django.http import HttpResponse
from django.db.models import Count
from uganda_common.utils import TIME_RANGES
from rapidsms_httprouter.models import Message
from ureport.models import MassText
from poll.models import Poll
from rapidsms.contrib.locations.models import Location
from django.conf import settings
from script.models import Script, ScriptStep
from poll.models import Category

try:
    from django.contrib.sites import Site
except ImportError:
    pass

DISEASE_CHOICES = [
    ('bd', 'int', 'Bloody diarrhea (Dysentery)', False),
    ('dy', 'int', 'Dysentery', False),
    ('ma', 'int', 'Malaria', False),
    ('tb', 'int', 'Tuberculosis', False),
    ('ab', 'int', 'Animal Bites', False),
    ('af', 'int', 'Acute Flaccid Paralysis (Polio)', False),
    ('mg', 'int', 'Meningitis', False),
    ('me', 'int', 'Measles', False),
    ('ch', 'int', 'Cholera', False),
    ('gw', 'int', 'Guinea Worm', False),
    ('nt', 'int', 'Neonatal Tetanus', False),
    ('yf', 'int', 'Yellow Fever', False),
    ('pl', 'int', 'Plague', False),
    ('ra', 'int', 'Rabies', False),
    ('rb', 'int', 'Rabies', False),
    ('vf', 'int', 'Other Viral Hemorrhagic Fevers', False),
    ('ei', 'int', 'Other Emerging Infectious Diseases', False),
]

HOME_ATTRIBUTES = [
   ('to', 'int', 'Total Homesteads Visited', False),
   ('it', 'int', 'ITTNs/LLINs', False),
   ('la', 'int', 'Latrines', False),
   ('ha', 'int', 'Handwashing Facilities', False),
   ('wa', 'int', 'Safe Drinking Water', False),
]

XFORMS = (
    ('', 'epi', ',;:*.\\s"', 'Epi Report', 'Weekly-submitted VHT epidemiological reports'),
    ('+', 'home', ',;:*.\\s"', 'Home Report', 'Monthly-submitted PVHT home visitation reports'),
    ('+', 'muac', ',;:*."', 'Malnu Report', 'VHT report of child malnutrition'),
    ('+', 'birth', ',;:*."', 'Birth Report', 'VHT report of a birth'),
    ('+', 'death', ',;:*."', 'Death Report', 'VHT report of a death'),
    ('+', 'itp', ',', 'Inpatient Treatment Report', 'Health Center report of an inpatient treatment',),
    ('+', 'otp', ',', 'Outpatient Treatment Report', 'Health Center report of an outpatient treatment',),
    ('+', 'cure', ',', 'Cure Treatment Report', 'Health Center report of patient cure',),
    ('+', 'reg', ',', 'Registration', 'Registers a reporter with their name',),
    ('+', 'pvht', ',', 'PVHT Signup', 'Registers a PVHT with their facility',),
    ('+', 'vht', ',', 'VHT Signup', 'Registers a VHT with their facility',),
    ('', 'com', ',;:*.\\s"', 'VHT Report', 'Routine VHT Report of weekly aggregate indicators'),
    ('', 'mal', ',;:*.\\s"', 'ITP/OTP Treatment Report', 'Routine HC report of weekly itp/otp treatments'),
    ('', 'rutf', ',;:*.\\s"', 'OTC/ITC Stock Report', 'Routine HC report of weekly otc/itc stock reports'),
    ('', 'act', ',;:*.\\s"', 'ACT Stock Report', 'Routine report of ACT stock'),
)

XFORM_FIELDS = {
    '+muac':[
         ('name', 'text', 'The name of the malnourished patient', True),
         ('gender', 'cvssex', 'The gender of the malnourished patient', True),
         ('age', 'cvstdelt', 'The age of the malnurished patient', True),
         ('category', 'cvsmuacr', 'Red, yellow, or green case of malnutrition', True),
         ('ignored', 'cvsodema', 'Occurence of oedema (T/F)', False),
     ],
    '+birth':[
         ('name', 'text', 'The name of the child born', True),
         ('gender', 'cvssex', 'The gender of the child born', True),
         ('place', 'cvsloc', 'At home or at a health facility', True),
     ],
     '+death':[
         ('name', 'text', 'The name of the person who has died', True),
         ('gender', 'cvssex', 'The gender of the person who has died', True),
         ('age', 'cvstdelt', 'The age of the person who has died', True),
     ],
    'epi':DISEASE_CHOICES,
    '+home':HOME_ATTRIBUTES,
    '+reg':[
         ('name', 'text', 'Your name', True),
    ],
    '+vht':[
         ('facility', 'facility', 'Your facility code', True),
    ],
    '+pvht':[
         ('facility', 'facility', 'Your facility code', True),
    ],
    'com':[
        ('fever', 'int', 'fever', True),
        ('diarrhea', 'int', 'diarrhea', True),
        ('death', 'int', 'deaths', True),
        ('bi_od', 'int', 'OE', True),
        ('muac_red', 'int', 'Red', True),
        ('muac_yellow', 'int', 'Yel', True),
        ('muac_green', 'int', 'Green', True),
    ],
    'mal':[
        ('total_new', 'int', 'new admissions', True),
        ('total_death', 'int', 'deaths', True),
        ('total_default', 'int', 'defaults', True),
        ('total_admissions', 'int', 'total admissions', True),
    ],
    'rutf':[
        ('new_f75_stock', 'int', 'F-75 New', True),
        ('closing_f75_stock', 'int', 'F-75 Balance', True),
        ('new_rutf_stock', 'int', 'RUTF New', True),
        ('closing_rutf_stock', 'int', 'RUTF Balance', True),
    ],
    'act':[
        ('yellow_disp', 'int', 'Yellow dispensed', True),
        ('yellow_balance', 'int', 'Yellow stock', True),
        ('blue_disp', 'int', 'Blue dispensed', True),
        ('blue_balance', 'int', 'Blue stock', True),
        ('brown_disp', 'int', 'Brown dispensed', True),
        ('brown_balance', 'int', 'Brown stock', True),
        ('green_disp', 'int', 'Green dispensed', True),
        ('green_balance', 'int', 'Green stock', True),
        ('other_disp', 'int', 'Other ACT dispensed', True),
        ('other_balance', 'int', 'Other ACT stock', True),
    ]
}

def init_xforms():
    init_xforms_from_tuples(XFORMS, XFORM_FIELDS)

def init_xforms_from_tuples(xforms, xform_fields):
    user = User.objects.get(username='admin')
    xform_dict = {}
    for keyword_prefix, keyword, separator, name, description in xforms:
        xform, created = XForm.objects.get_or_create(
            keyword=keyword,
            keyword_prefix=keyword_prefix,
            defaults={
                'name':name,
                'description':description,
                'response':'',
                'active':True,
                'owner':user,
                'site':Site.objects.get_current(),
                'separator':separator,
                'command_prefix':'',
            }
        )
        xform_dict["%s%s" % (keyword_prefix, keyword)] = xform

    for form_key, attributes in xform_fields.items():
        order = 0
        form = xform_dict[form_key]
        for command, field_type, description, required in attributes:
            xformfield, created = XFormField.objects.get_or_create(
                command=command,
                xform=form,
                defaults={
                    'order':order,
                    'field_type':field_type,
                    'type':field_type,
                    'name':description,
                    'description':description,
                }
            )
            if required:
                xformfieldconstraint, created = XFormFieldConstraint.objects.get_or_create(
                    field=xformfield,
                    defaults={
                        'type':'req_val',
                         'message':("Expected %s, none provided." % description)
                    }
            )
            order = order + 1
    return xform_dict


GROUP_BY_WEEK = 1
GROUP_BY_MONTH = 2
GROUP_BY_DAY = 16
GROUP_BY_QUARTER = 32

months = {
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
    GROUP_BY_DAY:('day', 'date(rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_WEEK:('week', 'extract(week from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_MONTH:('month', 'extract(month from rapidsms_xforms_xformsubmission.created)',),
    GROUP_BY_QUARTER:('quarter', 'extract(quarter from rapidsms_xforms_xformsubmission.created)',),
}

def total_submissions(keyword, start_date, end_date, location, extra_filters=None, group_by_timespan=None):
    if extra_filters:
        extra_filters = dict([(str(k), v) for k, v in extra_filters.items()])
        q = XFormSubmission.objects.filter(**extra_filters)
        tnum = 8
    else:
        q = XFormSubmission.objects
        tnum = 6
    select = {
        'location_name':'T%d.name' % tnum,
        'location_id':'T%d.id' % tnum,
        'rght':'T%d.rght' % tnum,
        'lft':'T%d.lft' % tnum,
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

    return q.filter(
               xform__keyword=keyword,
               has_errors=False,
               created__lte=end_date,
               created__gte=start_date).values(
               'connection__contact__reporting_location__name').extra(
               tables=['locations_location'],
               where=[\
                   'T%d.lft <= locations_location.lft' % tnum, \
                   'T%d.rght >= locations_location.rght' % tnum, \
                   location_children_where]).extra(\
               select=select).values(*values).annotate(value=Count('id')).extra(order_by=['location_name'])

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
    return  HealthProviderBase.objects.filter(groups=Group.objects.get(name='Village Health Team')).values('location__name').extra(
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

def total_attribute_value(attribute_slug, start_date, end_date, location, group_by_timespan=None):
    select = {
        'location_name':'T8.name',
        'location_id':'T8.id',
        'rght':'T8.rght',
        'lft':'T8.lft',
    }
    values = ['location_name', 'location_id', 'lft', 'rght']
    if group_by_timespan:
         select_value = GROUP_BY_SELECTS[group_by_timespan][0]
         select_clause = GROUP_BY_SELECTS[group_by_timespan][1]
         select.update({select_value:select_clause,
                        'year':'extract (year from rapidsms_xforms_xformsubmission.created)', })
         values.extend([select_value, 'year'])
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
               tables=['locations_location'],
               where=[\
                   'T8.lft <= locations_location.lft',
                   'T8.rght >= locations_location.rght',
                   location_children_where]).extra(\
               select=select).values(*values).annotate(value=Sum('value_int')).extra(order_by=['location_name'])

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

def reorganize_location(key, report, report_dict):
    for dict in report:
        location = dict['location_name']
        report_dict.setdefault(location, {'location_id':dict['location_id'], 'diff':(dict['rght'] - dict['lft'])})
        report_dict[location][key] = dict['value']

def reorganize_timespan(timespan, report, report_dict, location_list, request=None):
    for dict in report:
        time = dict[timespan]
        if timespan == 'month':
            time = datetime.datetime(int(dict['year']), int(time), 1)
        elif timespan == 'week':
            time = datetime.datetime(int(dict['year']), 1, 1) + datetime.timedelta(days=(int(time) * 7))
        elif timespan == 'quarter':
            time = datetime.datetime(int(dict['year']), int(time) * 3, 1)

        report_dict.setdefault(time, {})
        location = dict['location_name']
        report_dict[time][location] = dict['value']

        if not location in location_list:
            location_list.append(location)

def get_group_by(start_date, end_date):
    interval = end_date - start_date
    if interval <= datetime.timedelta(days=21):
        group_by = GROUP_BY_DAY
        prefix = 'day'
    elif datetime.timedelta(days=21) <= interval <= datetime.timedelta(days=90):
        group_by = GROUP_BY_WEEK
        prefix = 'week'
    elif datetime.timedelta(days=90) <= interval <= datetime.timedelta(days=270):
        group_by = GROUP_BY_MONTH
        prefix = 'month'
    else:
        group_by = GROUP_BY_QUARTER
        prefix = 'quarter'
    return {'group_by':group_by, 'group_by_name':prefix}

def get_reporters(**kwargs):
    request = kwargs.pop('request')
    if request.user.is_authenticated() and Location.objects.filter(type__name='district', name=request.user.username).count():
        area = Location.objects.filter(type__name='district', name=request.user.username)[0]
        return HealthProvider.objects.filter(reporting_location__in=area.get_descendants(include_self=True).all()).select_related('facility', 'location').annotate(Count('connection__submissions')).all()

    return HealthProvider.objects.select_related('facility', 'location').annotate(Count('connection__submissions')).all()

def get_messages(**kwargs):
    request = kwargs.pop('request')
    if request.user.is_authenticated() and Location.objects.filter(type__name='district', name=request.user.username).count():
        q = Location.objects.filter(type__name='district', name=request.user.username)
        if q.count():
            area = q[0]
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


models_created = []
structures_initialized = False

def init_cvsautoreg(sender, **kwargs):
    global models_created
    global structures_initialized
    models_created.append(sender.__name__)
    required_models = ['eav.models', 'poll.models', 'script.models', 'django.contrib.auth.models']
    if 'django.contrib.sites' in settings.INSTALLED_APPS:
        required_models.append('django.contrib.sites.models')
    if 'authsites' in settings.INSTALLED_APPS:
        required_models.append('authsites.models')
    for required in required_models:
        if required not in models_created:
            return
    if not structures_initialized:
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            site_id = getattr(settings, 'SITE_ID', 1)
            Site.objects.get_or_create(pk=site_id, defaults={'domain':'rapidcvs.org'})
        init_groups()
        init_autoreg(sender)
        structures_initialized = True

def init_groups():
    for g in ['VHT', 'PVHT', 'HC', 'HF', 'DHT', 'DHO', 'Other CVS Reporters']:
        Group.objects.get_or_create(name=g)

def init_autoreg(sender, **kwargs):
    script, created = Script.objects.get_or_create(
            slug="cvs_autoreg", defaults={
            'name':"Community Vulnerability Suveillance Script"})
    if created:
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            script.sites.add(Site.objects.get_current())
        user, created = User.objects.get_or_create(username="admin")

        ## role of CVS reporter
        role_poll = Poll.objects.create(
                            name='cvs_role', \
                            question='Welcome to RapidSMS, the Ministry of Health\'s data collection system. What is your role?', \
                            default_response='Thank you for starting the registration process', \
                            type=Poll.TYPE_TEXT, \
                            user=user\
                        )
        vht_category = role_poll.categories.create(name='VHT')
        vht_category.response = "Thank you for starting the registration process"
        vht_category.color = '99ff77'
        vht_category.save()
        pvht_category = role_poll.categories.create(name='PVHT')
        pvht_category.response = "Thank you for starting the registration process"
        pvht_category.color = 'ff9977'
        pvht_category.save()
        hc_category = role_poll.categories.create(name='HC')
        hc_category.response = "Thank you for starting the registration process"
        hc_category.color = 'ff7799'
        hc_category.save()
        hf_category = role_poll.categories.create(name='HF')
        hf_category.response = "Thank you for starting the registration process"
        hf_category.color = '77ff99'
        hf_category.save()
        dht_category = role_poll.categories.create(name='DHT')
        dht_category.response = "Thank you for starting the registration process"
        dht_category.color = '66ff99'
        dht_category.save()
        dho_category = role_poll.categories.create(name='DHO')
        dho_category.response = "Thank you for starting the registration process"
        dho_category.color = 'ff6699'
        dho_category.save()
        unknown_category = role_poll.categories.create(name='unknown')
        unknown_category.default = False
        unknown_category.color = 'ffff77'
        unknown_category.save()
        unclear_category = Category.objects.create(
            poll=role_poll,
            name='unclear',
            default=True,
            color='ffff77',
            response='We did not understand your answer. Kindly note that this number is for official use only',
            priority=3
        )

        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=role_poll,
            order=0,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=0,
            giveup_offset=60,
        ))

        ## CVS reporter Name
        name_poll = Poll.objects.create(
                            name='cvs_name', \
                            question='Please enter only the answers to the questions asked. What is your name?', \
                            type=Poll.TYPE_TEXT, \
                            user=user\
                        )

        script.steps.add(ScriptStep.objects.create(
               script=script,
               poll=name_poll,
               order=1,
               rule=ScriptStep.RESEND_GIVEUP,
               start_offset=0,
               retry_offset=60 * 15,
               giveup_offset=60 * 30,
               num_tries=3,
               ))

        ## CVS reporter District
        district_poll = Poll.objects.create(
                            name='cvs_district', \
                            question='What is the name of your District?', \
                            type='district', \
                            user=user\
                        )

        script.steps.add(ScriptStep.objects.create(
               script=script,
               poll=district_poll,
               order=2,
               rule=ScriptStep.RESEND_GIVEUP,
               start_offset=0,
               retry_offset=60 * 15,
               giveup_offset=60 * 30,
               num_tries=3,
               ))

        ## CVS reporter Health Facility
        hf_poll = Poll.objects.create(
                            name='cvs_healthfacility', \
                            question='What is the name of your Health Facility?', \
                            type=Poll.TYPE_TEXT, \
                            user=user\
                        )

        script.steps.add(ScriptStep.objects.create(
               script=script,
               poll=hf_poll,
               order=3,
               rule=ScriptStep.RESEND_GIVEUP,
               start_offset=0,
               retry_offset=60 * 15,
               giveup_offset=60 * 30,
               num_tries=3,
               ))

        ## CVS reporter Village
        village_poll = Poll.objects.create(
                            name='cvs_village', \
                            question='What is the name of your Village?', \
                            type=Poll.TYPE_TEXT, \
                            user=user\
                        )

        script.steps.add(ScriptStep.objects.create(
               script=script,
               poll=village_poll,
               order=4,
               rule=ScriptStep.RESEND_GIVEUP,
               start_offset=0,
               retry_offset=60 * 15,
               giveup_offset=60 * 30,
               num_tries=3,
               ))

        ## CVS reporter Thanks for registering message!
        script.steps.add(ScriptStep.objects.create(
               script=script,
               message='Thank you  for registering! You have just entered training mode.',
               order=6,
               rule=ScriptStep.WAIT_MOVEON,
               start_offset=0,
               giveup_offset=0,
               ))

        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            for poll in [role_poll, name_poll, district_poll, hf_poll, village_poll]:
                poll.sites.add(Site.objects.get_current())

        for poll in [role_poll, name_poll, district_poll, hf_poll, village_poll]:
            poll.start()
