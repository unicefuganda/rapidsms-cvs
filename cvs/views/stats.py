from healthmodels.models import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from healthmodels.models.HealthFacility import HealthFacility
from healthmodels.models.HealthProvider import HealthProvider
from simple_locations.models import AreaType,Point,Area
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect,HttpResponse
from cvs.utils import report, reorganize_location, reorganize_timespan, GROUP_BY_LOCATION, GROUP_BY_WEEK,GROUP_BY_MONTH, GROUP_BY_YEAR,GROUP_BY_DAY,GROUP_BY_QUARTER
from cvs.forms import DateRangeForm
import datetime
import time
from django.db import connection
from django.utils.datastructures import SortedDict

def index(request, location_id=None):
    """
        This is the basic stats page.  You can see that each column requires a separate
        call to report, but only once per column, not once per-column-per-location (same
        with the chart, no calls per week, month or quarter.
        
        FIXME: the proper GROUP_BY_xxx flags need to be used based on the date range
        passed from the user: If it's greater than nine months, it should probably
        be graphed quarterly, if it's greated than 3 months, monthly, if it's greater
        than 21 days, weekly, otherwise daily.
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

    max_date = datetime.datetime.now()
    
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]

    muac = report('muac', location=location, group_by = GROUP_BY_LOCATION, start_date=start_date, end_date=end_date,request=request)
    ma = report('epi', attribute_keyword='ma', location=location, group_by = GROUP_BY_LOCATION, start_date=start_date, end_date=end_date,request=request)
    tb = report('epi', attribute_keyword='tb', location=location, group_by = GROUP_BY_LOCATION, start_date=start_date, end_date=end_date,request=request)
    bd = report('epi', attribute_keyword='bd', location=location, group_by = GROUP_BY_LOCATION, start_date=start_date, end_date=end_date,request=request)
    birth = report('birth', location=location, group_by = GROUP_BY_LOCATION, start_date=start_date, end_date=end_date,request=request)
    death = report('death', location=location, group_by = GROUP_BY_LOCATION, start_date=start_date, end_date=end_date,request=request)
    to = report('home', attribute_keyword='to', location=location, group_by = GROUP_BY_LOCATION, start_date=start_date, end_date=end_date,request=request)
    wa = report('home', attribute_keyword='wa', location=location, group_by = GROUP_BY_LOCATION, start_date=start_date, end_date=end_date,request=request)
    report_dict = SortedDict()
    reorganize_location('muac', muac, report_dict)
    reorganize_location('ma', ma, report_dict)
    reorganize_location('tb', tb, report_dict)
    reorganize_location('bd', bd, report_dict)
    reorganize_location('birth', birth, report_dict)
    reorganize_location('death', death, report_dict)
    reorganize_location('to', to, report_dict)
    reorganize_location('wa', wa, report_dict)
    # label, link, colspan
    topColumns = (('','',1),
                  ('Malnutrition', '/cvs/muac/', 1),
                  ('Epi','/cvs/epi/',3),
                  ('Birth','/cvs/birth/',1),
                  ('Death','/cvs/death/',1),
                  ('Home', '/cvs/home/',1),
                  ('Reporters','/cvs/reporters/',1)
                  )
    # label, link, colspan, onclick
    columns = (('','',1),
               ('Total New Cases','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/')"),
               ('Malaria','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/ma/')"),
               ('Tb','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/tb/')"),
               ('Bloody Diarrhea','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/bd/')"),
               ('Total','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/')"),
               ('Total Child Deaths','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/death/')"),
               ('Safe Drinking Water (% of homesteads)','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/wa/')"),
               ('% of expected weekly Epi reports received','javascript:void(0)',1,''),
    )
    interval=end_date-start_date
    if interval<=datetime.timedelta(days=21):
        group_by=GROUP_BY_DAY
        r='day'
    elif datetime.timedelta(days=21) <=interval<=datetime.timedelta(days=90):
        group_by=GROUP_BY_WEEK
        r='week'
    elif datetime.timedelta(days=90) <=interval<=datetime.timedelta(days=270):
        group_by=GROUP_BY_MONTH
        r='month'
    else:
        group_by=GROUP_BY_QUARTER
        r='quarter'


    chart = report('epi', location=location, attribute_keyword='ma', start_date=start_date, end_date=end_date, group_by=group_by | GROUP_BY_LOCATION )
    chart_title = 'Variation of Malaria Reports'
    xaxis = 'Week of Year'
    yaxis = 'Number of Cases'
    chart_dict = SortedDict()
    location_list = []
    reorganize_timespan(r, chart, chart_dict, location_list)    
    return render_to_response("cvs/stats.html",
                              {'report':report_dict, 
                               'top_columns':topColumns, 
                               'columns':columns, 
                               'location_id':location_id, 
                               'report_template':'cvs/partials/stats_main.html', 
                               'data':chart_dict, 
                               'series':location_list, 
                               'start_date':start_date, 
                               'end_date':end_date, 
                               'xaxis':xaxis, 
                               'yaxis':yaxis, 
                               'chart_title': chart_title,
                               'tooltip_prefix': '',
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(min_date.timetuple()) * 1000,
                               'start_ts':time.mktime(start_date.timetuple()) * 1000,
                               'end_ts':time.mktime(end_date.timetuple()) * 1000,
                               'date_range_form':form,
                                }, context_instance=RequestContext(request))



def muac_detail(request,location_id=None):
    
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

    max_date = datetime.datetime.now()

    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]

    return render_to_response("cvs/stats.html")





