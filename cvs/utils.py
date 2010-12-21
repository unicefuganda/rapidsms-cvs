from django.db.models import Sum
from django.db.models import Q
from django.db import connection

from rapidsms_xforms.models import *
import datetime

GROUP_BY_WEEK = 1
GROUP_BY_MONTH = 2
GROUP_BY_YEAR = 4
GROUP_BY_LOCATION = 8

def report(xform_keyword, start_date=None, end_date=datetime.datetime.now(), attribute_keyword=None, location=None, facility=None, group_by=None):
    """
        select count(submissions.id), extract(week from submissions.created) as week, extract(year from submissions.created) as year from rapidsms_xforms_xformsubmission submissions join rapidsms_xforms_xform xforms on submissions.xform_id = xforms.id where xforms.keyword = 'muac' group by extract(week from submissions.created), extract(year from submissions.created) order by year, week;
    """
    if group_by is not None:
        return report_raw(xform_keyword, group_by, start_date, end_date, attribute_keyword, location, facility)
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
        return values.aggregate(Sum('value_int'))['value_int__sum']

def report_raw(xform_keyword, group_by, start_date=None, end_date=None, attribute_keyword=None, location=None, facility=None):
    cursor = connection.cursor()
    groupby_columns = []
    orderby_columns = []
    if attribute_keyword is not None:
        select_clauses = [('sum(value_int)', 'sum',)]
        root_table = "eav_value as values"
        where_clauses = ["attributes.slug = '%s_%s'" % (xform_keyword, attribute_keyword)]
        joins = ['eav_attribute attributes on values.attribute_id = attributes.id', 'rapidsms_xforms_xformsubmission submissions on values.entity_id = submissions.id']
    else:
        select_clauses = [('count(submissions.id)', 'count',)]
        root_table = 'rapidsms_xforms_xformsubmission as submissions'
        where_clauses = ["xforms.keyword = '%s'" % xform_keyword] 
        joins = ['rapidsms_xforms_xform xforms on submissions.xform_id = xforms.id']
    if location is not None:
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
    if group_by & GROUP_BY_MONTH:
        select_clauses.append(('extract(month from submission.created)', 'month'))
        groupby_columns.append('month')
        orderby_columns.append('month')        
    if group_by & GROUP_BY_LOCATION:
        select_clauses.append(('locations.name', 'lname',))
        groupby_columns.append('lname')
        orderby_columns.append('lname')
        joins.append('rapidsms_connection connections on submissions.connection_id = connections.id')
        joins.append('healthmodels_healthproviderbase providers on connections.contact_id = providers.contact_ptr_id')
        if location is None:
            joins.append('simple_locations_area locations on providers.location_id = locations.id')
        else:
            joins.append('simple_locations_area locations on providers.location_id >= locations.lft and providers.location_id <= locations.rght')

    sql = "select " + ' , '.join(["%s as %s" % (column, alias) for column, alias in select_clauses])
    sql += " from " + root_table
    if len(joins):
        sql += " join " + ' join '.join(joins)
    sql += " where " + ' and '.join(where_clauses)
    if len(groupby_columns):
        sql += " group by " + ' , '.join(groupby_columns)
    if len(orderby_columns):
        sql += " order by " + ' , '.join(orderby_columns)
    cursor.execute(sql)
    list_toret = []
    for row in cursor.fetchall():
        if attribute_keyword is not None:
            rowdict = {'sum':row[0]}
        else:
            rowdict = {'count':row[0]}
        rowoff = 1
        if group_by & GROUP_BY_YEAR:
            rowdict.update({'year':row[rowoff]})
            rowoff += 1
        if group_by & GROUP_BY_MONTH:
            rowdict.update({'month':row[rowoff]})
            rowoff += 1
        if group_by & GROUP_BY_WEEK:
            rowdict.update({'week':row[rowoff]})
            rowoff += 1
        if group_by & GROUP_BY_LOCATION:
            rowdict.update({'location_name':row[rowoff]})
            rowoff += 1
        list_toret.append(rowdict)
    return list_toret
