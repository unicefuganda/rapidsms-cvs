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

def init_xforms():
    DISEASE_CHOICES = [
        ('bd','int','Bloody diarrhea (Dysentery)'),
        ('ma','int','Malaria'),
        ('tb','int','Tuberculosis'),
        ('ab','int','Animal Bites'),
        ('af','int','Acute Flaccid Paralysis (Polio)'),
        ('mg','int','Meningitis'),
        ('me','int','Measles'),
        ('ch','int','Cholera'),
        ('gw','int','Guinea Worm'),
        ('nt','int','Neonatal Tetanus'),
        ('yf','int','Yellow Fever'),
        ('pl','int','Plague'),
        ('ra','int','Rabies'),
        ('vf','int','Other Viral Hemorrhagic Fevers'),
        ('ei','int','Other Emerging Infectious Diseases'),
    ]

    HOME_ATTRIBUTES = [
       ('to','int','Total Homesteads Visited'),
       ('it','int','ITTNs/LLINs'),
       ('la','int','Latrines'),
       ('ha','int','Handwashing Facilities'),
       ('wa','int','Safe Drinking Water'),
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
             ('name', 'text', 'The name of the malnourished patient'),
             ('gender', 'cvssex','The gender of the malnourished patient'),
             ('age', 'cvstdelt', 'The age of the malnurished patient'),
             ('category','cvsmuacr', 'Red, yellow, or green case of malnutrition'),
             ('ignored','cvsodema', 'Occurence of oedema (T/F)')
         ],
        'birth':[
             ('name', 'text', 'The name of the child born'),
             ('gender', 'cvssex', 'The gender of the child born'),
             ('place','cvsloc', 'At home or at a health facility'),
         ],
         'death':[
             ('name','text','The name of the person who has died'),
             ('gender', 'cvssex', 'The gender of the person who has died'),
             ('age', 'cvstdelt', 'The age of the person who has died'),
         ],
        'epi':DISEASE_CHOICES,
        'home':HOME_ATTRIBUTES,
        'reg':[
             ('name','text','The name of the reporter registering'),
        ],
        'vht':[
             ('facility','facility','The facility of the vht signing up'),
        ],
        'pvht':[
             ('facility','facility','The facility of the pvht signing up'),
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
            order = order + 1
    return xform_dict


GROUP_BY_WEEK = 1
GROUP_BY_MONTH = 2
GROUP_BY_YEAR = 4
GROUP_BY_LOCATION = 8
GROUP_BY_DAY = 16
GROUP_BY_QUARTER = 32
GROUP_BY_FACILITY = 64

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

def report(xform_keyword, start_date=None, end_date=datetime.datetime.now(), attribute_keyword=None, attribute_value=None, location=None, facility=None, group_by=None,**kwargs):
    """
        
    """
    request=kwargs.get('request',None)
    if group_by is not None:
        return report_raw(xform_keyword, group_by, start_date, end_date, attribute_keyword, attribute_value, location, facility,**kwargs)
    if attribute_keyword is None:
        submissions = XFormSubmission.objects.filter(xform__keyword=xform_keyword)
        if start_date is not None:
            submissions = submissions.filter(created__gt=start_date, created__lte=end_date)
        if location is not None:
            submissions = submissions.filter(Q(connection__contact__healthproviderbase__healthprovider__location=location) | Q(connection__contact__healthproviderbase__healthprovider__location__in=location.get_descendants()))
        if facility is not None:
            submissions = submissions.filter(Q(connection__contact__healthproviderbase__healthprovider__facility=facility) | 
                                   Q(connection__contact__healthproviderbase__healthprovider__location__in=facility.catchment_areas.all()))            
        return submissions.count()
    else:
        attribute_slug = "%s_%s" % (xform_keyword, attribute_keyword)
        values = XFormSubmissionValue.objects.filter(attribute__slug=attribute_slug)
        if start_date is not None:
            values = values.filter(submission__created__gt=start_date, submission__created__lte=end_date)
        if location is not None:
            values = values.filter(Q(submission__connection__contact__healthproviderbase__healthprovider__location=location) | Q(submission__connection__contact__healthproviderbase__healthprovider__location__in=location.get_descendants()))
        if facility is not None:
            values = values.filter(Q(submission__connection__contact__healthproviderbase__healthprovider__facility=facility) | 
                                   Q(submission__connection__contact__healthproviderbase__healthprovider__location__in=facility.catchment_areas.all()))
        if attribute_value is not None:
            values = values.filter(value_text=attribute_value)
            return values.count()
        return values.aggregate(Sum('value_int'))['value_int__sum']

def report_raw(xform_keyword, group_by, start_date=None, end_date=None, attribute_keyword=None, attribute_value=None, location=None, facility=None,**kwargs):

    cursor = connection.cursor()
    list_toret = []
    countx = None
    if isinstance(attribute_keyword, list) and isinstance(attribute_value, list):
        sql = mk_entity_raw_sql(xform_keyword, group_by, start_date, end_date, attribute_keyword[0], attribute_value[0], location, facility,**kwargs)
        cursor.execute(sql)
        k = 1
        while k < len(attribute_keyword):
            countx = 0
            for row in cursor.fetchall():
                attribute_slug = "%s_%s" % (xform_keyword, attribute_keyword[k])
                value = XFormSubmissionValue.objects.filter(entity_id=row[0], attribute__slug=attribute_slug, value_text=attribute_value[k])
                countx += value.count()
            k +=1
    else:
        sql = mk_raw_sql(xform_keyword, group_by, start_date, end_date, attribute_keyword, attribute_value, location, facility,**kwargs)
    cursor.execute(sql)
    for row in cursor.fetchall():
        if countx is None:
            rowdict = {'value':row[0]}
        else:
            rowdict = {'value':countx}
        rowoff = 1
        if group_by & GROUP_BY_YEAR:
            rowdict.update({'year':row[rowoff]})
            rowoff += 1

        if group_by & GROUP_BY_WEEK:
            rowdict.update({'week':row[rowoff]})
            rowoff += 1            
        if group_by & GROUP_BY_MONTH:
            rowdict.update({'month':row[rowoff]})
            rowoff += 1
        if group_by & GROUP_BY_DAY:
            rowdict.update({'day':row[rowoff]})
            rowoff += 1
        if group_by & GROUP_BY_QUARTER:
            rowdict.update({'quarter':row[rowoff]})
            rowoff += 1
        if group_by & GROUP_BY_LOCATION:
            rowdict.update({'location_name':row[rowoff]})
            rowoff += 1
            rowdict.update({'location_id':row[rowoff]})
            rowoff += 1
            rowdict.update({'rght':row[rowoff]})
            rowoff += 1
            rowdict.update({'lft':row[rowoff]})
            rowoff += 1
        if group_by & GROUP_BY_FACILITY:
            rowdict.update({'facility_name':row[1]})
            rowdict.update({'facility_id':row[2]})
            rowdict.update({'type':row[3]})
            rowdict.update({'latitude':row[4]})
            rowdict.update({'longitude':row[5]})
        list_toret.append(rowdict)
    return list_toret

def mk_raw_sql(xform_keyword, group_by, start_date=None, end_date=None, attribute_keyword=None, attribute_value=None, location=None, facility=None,**kwargs):

    """
        report_raw returns a list of dictionaries, each with keys based on the GROUP_BY_xxxx flags used.
        all dictionaries will at least contain a "value" key, which is the count() of reports or the sum() of a particular
        attribute for a particular report.
        For instance, report_raw('epi', group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION, attribute_keyword='ma') would return a list of
        dictionaries of the form:
        [{'location_id':1,'location_name':'Uganda','week':1,'value':13},
        ...
        ]
        where '13' is the total number of cases of malaria in Uganda (in this case, we didn't filter by
        time, so in fact 13 would be the total number of cases reported for the entire database in Uganda.
        
        Note how the SQL raw query is composed of select_clauses, joins, where_clauses, orderby_columns,
        and groupby_columns.  This can be modified to suit even more particular cases (for instance, maybe
        counting the number of occurences of a particular attribute having a particular value, like total
        birth reports with gender == 'M'
    """
    groupby_columns = []
    orderby_columns = []
    if attribute_keyword is not None:
        root_table = "eav_value as values"
        where_clauses = ["attributes.slug = '%s_%s'" % (xform_keyword, attribute_keyword)]
        joins = ['eav_attribute attributes on values.attribute_id = attributes.id', 'rapidsms_xforms_xformsubmission submissions on values.entity_id = submissions.id']
        if attribute_value is not None:
            if isinstance(attribute_value, dict):
                select_clauses = [('count(value_int)', 'value',)]
                func = attribute_value.keys()
                if isinstance(attribute_value[func[0]], list):
                    attribute_values = tuple(attribute_value[func[0]])
                else:
                    attribute_values = attribute_value[func[0]]
                if func[0] == 'under':
                    where_clauses.append("values.value_int < %d" % attribute_values)
                elif func[0] == 'above':
                    where_clauses.append("values.value_int > %d" % attribute_values)
                else:
                    where_clauses.append("values.value_int between %d and %d" % attribute_values)
            elif isinstance(attribute_value, tuple):
                select_clauses = [('count(value_text)', 'value',)]
                where_clauses.append("values.value_text in ('%s','%s')" % attribute_value)
            else:
                select_clauses = [('count(value_text)', 'value',)]
                where_clauses.append("values.value_text = '%s'" % attribute_value)
        else:
            select_clauses = [('sum(value_int)', 'value',)]        
    else:
        select_clauses = [('count(submissions.id)', 'value',)]
        root_table = 'rapidsms_xforms_xformsubmission as submissions'
        where_clauses = ["xforms.keyword = '%s'" % xform_keyword] 
        joins = ['rapidsms_xforms_xform xforms on submissions.xform_id = xforms.id']
    if location is not None:
        if kwargs.get('request',None) and kwargs.get('request',None) and kwargs['request'].GET.get('root',None):
             group_by = group_by | GROUP_BY_LOCATION
             where_clauses.append("locations.id in (%s)" % location.id)
        else:
            group_by = group_by | GROUP_BY_LOCATION
            where_clauses.append("locations.id in (%s)" % ' , '.join(str(id) for id in location.get_children().values_list('pk', flat=True)))
    
    # Only use non-duplicate submissions
    where_clauses.append('not submissions.has_errors')

    if start_date is not None:
        where_clauses.append("submissions.created >= date '%s'" % datetime.datetime.strftime(start_date, '%Y-%m-%d'))
        where_clauses.append("submissions.created <= date '%s'" % datetime.datetime.strftime(end_date, '%Y-%m-%d'))
    if facility is not None:
        group_by = group_by | GROUP_BY_LOCATION
        where_clauses.append("(providers.location_id in (%s) or providers.facility_id = %s)" % (' , '.join(str(id) for id in facility.catchment_areas.all()), str(facility.pk)))
    if group_by & GROUP_BY_YEAR:
        select_clauses.append(('extract(year from submissions.created)', 'year',))
        groupby_columns.append('year')
        orderby_columns.append('year')    
    if group_by & GROUP_BY_WEEK:
        select_clauses.append(('extract(week from submissions.created)', 'week',))
        groupby_columns.append('week')
        orderby_columns.append('week')        
    if group_by & GROUP_BY_MONTH:
        select_clauses.append(('extract(month from submissions.created)', 'month'))
        groupby_columns.append('month')
        orderby_columns.append('month')
    if group_by & GROUP_BY_DAY:
#        select_clauses.append(('extract(day from submissions.created)', 'day'))
        select_clauses.append(('submissions.created' , 'day',))
        groupby_columns.append('day')
        orderby_columns.append('day')
    if group_by & GROUP_BY_QUARTER:
           select_clauses.append(('extract(quarter from submissions.created)', 'quarter'))
           groupby_columns.append('quarter')
           orderby_columns.append('quarter')
    if group_by & GROUP_BY_FACILITY:
        select_clauses.append(('facility.name', 'fname',))
        select_clauses.append(('providers.facility_id', 'fid',))
        select_clauses.append(('type.name', 'tname',))
        select_clauses.append(('location.latitude', 'latitude',))
        select_clauses.append(('location.longitude', 'longitude',))
        groupby_columns.append('fname')
        groupby_columns.append('tname')
        groupby_columns.append('fid')
        groupby_columns.append('latitude')
        groupby_columns.append('longitude')
        orderby_columns.append('value DESC')
        where_clauses.append('location.latitude >=%s'% kwargs.get('minLat'))
        where_clauses.append('location.latitude <=%s'% kwargs.get('maxLat'))
        where_clauses.append('location.longitude >=%s'%kwargs.get('minLon'))
        where_clauses.append('location.longitude <=%s'%kwargs.get('maxLon'))
        joins.append('rapidsms_connection connections on submissions.connection_id = connections.id')
        joins.append('healthmodels_healthproviderbase providers on connections.contact_id = providers.contact_ptr_id')
        joins.append('healthmodels_healthfacilitybase facility on providers.facility_id = facility.id')
        joins.append(' healthmodels_healthfacilitytypebase type on type.id = facility.type_id')
        joins.append(' simple_locations_point location on facility.location_id = location.id')

    if group_by & GROUP_BY_LOCATION:
        select_clauses.append(('locations.name', 'lname',))
        select_clauses.append(('locations.id', 'lid',))
        select_clauses.append(('locations.lft', 'lft',))
        select_clauses.append(('locations.rght', 'rght',))
        groupby_columns.append('lname')
        groupby_columns.append('lid')
        groupby_columns.append('locations.lft')
        groupby_columns.append('locations.rght')
        orderby_columns.append('lname')
        joins.append('rapidsms_connection connections on submissions.connection_id = connections.id')
        joins.append('healthmodels_healthproviderbase providers on connections.contact_id = providers.contact_ptr_id')
        if location is None:
            joins.append('simple_locations_area locations on providers.location_id = locations.id')
        else:
            joins.append('simple_locations_area provider_locations on providers.location_id = provider_locations.id')
            joins.append('simple_locations_area locations on provider_locations.lft >= locations.lft and provider_locations.rght <= locations.rght')

#    if attribute_keyword is not None:
#        groupby_columns.append('entity')
    
    sql = "select " + ' , '.join(["%s as %s" % (column, alias) for column, alias in select_clauses])
    sql += " from " + root_table
    if len(joins):
        sql += " join " + ' join '.join(joins)
    sql += " where " + ' and '.join(where_clauses)
    if len(groupby_columns):
        sql += " group by " + ' , '.join(groupby_columns)
    if len(orderby_columns):
        sql += " order by " + ' , '.join(orderby_columns)
    return sql

def mk_entity_raw_sql(xform_keyword, group_by, start_date=None, end_date=None, attribute_keyword=None, attribute_value=None, location=None, facility=None,**kwargs):
    groupby_columns = []
    orderby_columns = []
    if attribute_keyword is not None:
        root_table = "eav_value as values"
        where_clauses = ["attributes.slug = '%s_%s'" % (xform_keyword, attribute_keyword)]
        joins = ['eav_attribute attributes on values.attribute_id = attributes.id', 'rapidsms_xforms_xformsubmission submissions on values.entity_id = submissions.id']
        if attribute_value is not None:
            select_clauses = [('entity_id', 'entity',)]
            where_clauses.append("values.value_text = '%s'" % attribute_value)
        else:
            select_clauses = [('entity_id', 'entity',)]        
    else:
        select_clauses = [('count(submissions.id)', 'value',)]
        root_table = 'rapidsms_xforms_xformsubmission as submissions'
        where_clauses = ["xforms.keyword = '%s'" % xform_keyword] 
        joins = ['rapidsms_xforms_xform xforms on submissions.xform_id = xforms.id']
    if location is not None:
        if kwargs.get('request',None) and kwargs['request'] and  kwargs['request'].GET.get('root',None):
             group_by = group_by | GROUP_BY_LOCATION
             where_clauses.append("locations.id in (%s)" % location.id)
        else:
            group_by = group_by | GROUP_BY_LOCATION
            where_clauses.append("locations.id in (%s)" % ' , '.join(str(id) for id in location.get_children().values_list('pk', flat=True)))


    if start_date is not None:
        where_clauses.append("submissions.created >= date '%s'" % datetime.datetime.strftime(start_date, '%Y-%m-%d'))
        where_clauses.append("submissions.created <= date '%s'" % datetime.datetime.strftime(end_date, '%Y-%m-%d'))
    if facility is not None:
        group_by = group_by | GROUP_BY_LOCATION
        where_clauses.append("(providers.location_id in (%s) or providers.facility_id = %s)" % (' , '.join(str(id) for id in facility.catchment_areas.all()), str(facility.pk)))
    if group_by & GROUP_BY_YEAR:
        select_clauses.append(('extract(year from submissions.created)', 'year',))
        groupby_columns.append('year')
        orderby_columns.append('year')    
    if group_by & GROUP_BY_WEEK:
        select_clauses.append(('extract(week from submissions.created)', 'week',))
        groupby_columns.append('week')
        orderby_columns.append('week')        
    if group_by & GROUP_BY_MONTH:
        select_clauses.append(('extract(month from submissions.created)', 'month'))
        groupby_columns.append('month')
        orderby_columns.append('month')
    if group_by & GROUP_BY_DAY:
#        select_clauses.append(('extract(day from submissions.created)', 'day'))
        select_clauses.append(('submissions.created' , 'day',))
        groupby_columns.append('day')
        orderby_columns.append('day')
    if group_by & GROUP_BY_LOCATION:
        select_clauses.append(('locations.name', 'lname',))
        select_clauses.append(('locations.id', 'lid',))
        select_clauses.append(('locations.lft', 'lft',))
        select_clauses.append(('locations.rght', 'rght',))
        groupby_columns.append('lname')
        groupby_columns.append('lid')
        orderby_columns.append('lname')
        groupby_columns.append('locations.lft')
        groupby_columns.append('locations.rght')
        joins.append('rapidsms_connection connections on submissions.connection_id = connections.id')
        joins.append('healthmodels_healthproviderbase providers on connections.contact_id = providers.contact_ptr_id')
        if location is None:
            joins.append('simple_locations_area locations on providers.location_id = locations.id')
        else:
            joins.append('simple_locations_area locations on providers.location_id >= locations.lft and providers.location_id <= locations.rght')

    if attribute_keyword is not None:
        groupby_columns.append('entity')
    
    sql = "select " + ' , '.join(["%s as %s" % (column, alias) for column, alias in select_clauses])
    sql += " from " + root_table
    if len(joins):
        sql += " join " + ' join '.join(joins)
    sql += " where " + ' and '.join(where_clauses)
    if len(groupby_columns):
        sql += " group by " + ' , '.join(groupby_columns)
    if len(orderby_columns):
        sql += " order by " + ' , '.join(orderby_columns)
    
    return sql

def reorganize_location(key, report, report_dict):
    for dict in report:
        location = dict['location_name']
        report_dict.setdefault(location,{'location_id':dict['location_id']})
        report_dict[location][key] = dict['value']
        
def reorganize_timespan(timespan, report, report_dict, location_list,request=None):
    for dict in report:
        time = dict[timespan]
        if timespan =='month':
            time = months[int(time)]
        elif timespan =='week':
            time = 'Week '+str(int(time))
        elif timespan =='quarter':
            time = quarters[int(time)]+ ' Quarter'
        else:
            format = '%d-%m-%Y'
            time = time.strftime(format)
#            dates = get_dates(request)
#            start_year, start_month, start_day = dates['start'].year, dates['start'].month, dates['start'].day
#            end_year, end_month, end_day = dates['end'].year, dates['end'].month, dates['end'].day
#            if time == start_day:
#                time= str(int(time)) +'-'+ str(start_month) +'-'+ str(start_year)
#            else:
#                time= str(int(time)) +'-'+ str(end_month) +'-'+ str(end_year)


        report_dict.setdefault(time,{})
        location = dict['location_name']
        report_dict[time][location] = dict['value']

        if not location in location_list:
            location_list.append(location)
    
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
    else:
        form = DateRangeForm()
        cursor = connection.cursor()
        cursor.execute("select min(created), max(created) from rapidsms_xforms_xformsubmission")
        min_date, end_date = cursor.fetchone()
        start_date = end_date - datetime.timedelta(days=30)
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


