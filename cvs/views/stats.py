from healthmodels.models import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from healthmodels.models.HealthFacility import HealthFacility
from healthmodels.models.HealthProvider import HealthProvider
from simple_locations.models import AreaType,Point,Area
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect,HttpResponse
from cvs.utils import report, reorganize_location, reorganize_timespan, get_dates, get_expected_epi, GROUP_BY_LOCATION, GROUP_BY_WEEK,GROUP_BY_MONTH, GROUP_BY_YEAR,GROUP_BY_DAY,GROUP_BY_QUARTER
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
    
    dates = get_dates(request)
    max_date = datetime.datetime.now()
    
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]

    muac = report('muac', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    ma = report('epi', attribute_keyword='ma', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    tb = report('epi', attribute_keyword='tb', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    bd = report('epi', attribute_keyword='bd', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    birth = report('birth', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    death = report('death', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    percentage_safe_water = report('home', attribute_keyword='wa', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    home_total = report('home', attribute_keyword='to', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    percentage_epi = report('epi', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    expected_epi = get_expected_epi(location,request)

    x = 0
    while x < len(percentage_safe_water):
        home_divide = float(percentage_safe_water[x]['value'])
        total_value = float(home_total[x]['value'])
        home_divide /= total_value
        percentage_safe_water[x]['value'] = round(home_divide*100,1)
        x +=1

    y = 0
    while y < len(percentage_epi):
        epi_divide = float(percentage_epi[y]['value'])
        epi_divide /= expected_epi
        percentage_epi[y]['value'] = round(epi_divide*100,1)
        y +=1

    report_dict = SortedDict()
    reorganize_location('muac', muac, report_dict)
    reorganize_location('ma', ma, report_dict)
    reorganize_location('tb', tb, report_dict)
    reorganize_location('bd', bd, report_dict)
    reorganize_location('birth', birth, report_dict)
    reorganize_location('death', death, report_dict)
    reorganize_location('percentage_epi', percentage_epi, report_dict)
    reorganize_location('percentage_safe_water', percentage_safe_water, report_dict)
    # label, link, colspan
    topColumns = (('','',1),
                  ('Malnutrition', '/cvs/muac/', 1),
                  ('Epi','/cvs/epi/',3),
                  ('Birth','/cvs/birth/',1),
                  ('Death','/cvs/death/',1),
                  ('Home', '/cvs/home/',1),
                  ('Reporters','/cvs/reporter/',1)
                  )
                  
    columns = (
               ('','',1,''),
               ('Total New Cases','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/')"),
               ('Malaria','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/ma/')"),
               ('Tb','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/tb/')"),
               ('Bloody Diarrhea','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/bd/')"),
               ('Total','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/')"),
               ('Total Child Deaths','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/death/')"),
               ('Safe Drinking Water (% of homesteads)','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/wa/percentage/')"),
               ('% of expected weekly Epi reports received','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/percentage/')"),
    )
    interval=dates['end']-dates['start']
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


    chart = report('epi', location=location, attribute_keyword='ma', start_date=dates['start'], end_date=dates['end'], group_by=group_by | GROUP_BY_LOCATION )
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
                               'start_date':dates['start'], 
                               'end_date':dates['end'], 
                               'xaxis':xaxis, 
                               'yaxis':yaxis, 
                               'chart_title': chart_title,
                               'tooltip_prefix': '',
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                                }, context_instance=RequestContext(request))

def muac_detail(request,location_id=None):
    """
    malnutrition stats
    """
    dates = get_dates(request)
    max_date = datetime.datetime.now()   
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]
    total = report('muac', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    green = report('muac', attribute_keyword='category', attribute_value='G', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    green_oedema = report('muac', attribute_keyword=['category', 'oedema'], attribute_value=['G','T'], location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    yellow = report('muac', attribute_keyword='category', attribute_value='Y', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    red = report('muac', attribute_keyword='category', attribute_value='R', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    red_oedema = report('muac', attribute_keyword=['category', 'oedema'], attribute_value=['R','T'], location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    report_dict = {}
    reorganize_location('total', total, report_dict)
    reorganize_location('green', green, report_dict)
    reorganize_location('green_oedema', green_oedema, report_dict)
    reorganize_location('yellow', yellow, report_dict)
    reorganize_location('red', red, report_dict)
    reorganize_location('red_oedema', red_oedema, report_dict)
    
    columns = (('','',1),
                  ('Total', '', 1),
                  ('Green','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/category/G/')"),
                  ('Green+oe','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/category__oedema/G__T/')"),
                  ('Yellow','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/category/Y/')"),
                  ('Red','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/category/R/')"),
                  ('Red+oe','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/category__oedema/R__T/')")
                  )
    
    chart = report('muac', location=location, start_date=dates['start'], end_date=dates['end'], group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION | GROUP_BY_YEAR)
    chart_title = 'Variation of Total Malnutrition Reports'
    xaxis = 'Week of Year'
    yaxis = 'Number of Cases'
    chart_dict = {}
    location_list = []
    reorganize_timespan('week', chart, chart_dict, location_list)  
    
    return render_to_response("cvs/stats.html",
                              {'report':report_dict, 
                               'columns':columns,  
                               'location_id':location_id, 
                               'report_template':'cvs/partials/muac_main.html',
                               'data':chart_dict, 
                               'series':location_list, 
                               'start_date':dates['start'], 
                               'end_date':dates['end'], 
                               'xaxis':xaxis, 
                               'yaxis':yaxis, 
                               'chart_title': chart_title,
                               'tooltip_prefix': 'Week ', 
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                                }, context_instance=RequestContext(request))

def epi_detail(request, location_id=None):
    """
    epi stats
    """
    dates = get_dates(request)
    max_date = datetime.datetime.now()
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]
    categories = (
                  ('bd','Bloody Diarrhea'),
                  ('ma','Malaria'), 
                  ('tb','Tb'), 
                  ('ab','Animal Bite'), 
                  ('af','Polio'), 
                  ('mg','Meningitis'), 
                  ('me','Measles'), 
                  ('ch','Cholera'), 
                  ('gw','Ginuea Worm'), 
                  ('nt','Neonatal Tetanus'), 
                  ('yf','Yellow Fever'), 
                  ('pl','Plague'), 
                  ('ra','Rabies'), 
                  ('vf','Hemorrhagic Fevers'), 
                  ('ei','Infectious Diseases')
    )
    report_dict = {}
    total = report('epi', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    reorganize_location('total', total, report_dict)
    for attrib_keyword, v in categories:
        dictx = report('epi', attribute_keyword=attrib_keyword, location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
        reorganize_location(attrib_keyword, dictx, report_dict)

    columns = [('','',1),('Total','',1)]
    for k, v in categories:
        link = 'javascript:void(0)'
        colspan = 1
        onclick = "loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/"+k+"/')"
        tup = (v, link, colspan, onclick)
        columns.append(tup)
    
    chart = report('epi', location=location, start_date=dates['start'], end_date=dates['end'], group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION | GROUP_BY_YEAR)
    chart_title = 'Variation of Total Epi Reports'
    xaxis = 'Week of Year'
    yaxis = 'Number of Cases'
    chart_dict = {}
    location_list = []
    reorganize_timespan('week', chart, chart_dict, location_list)
    
    return render_to_response("cvs/stats.html",
                              {'report':report_dict, 
                               'columns':columns,  
                               'location_id':location_id, 
                               'report_template':'cvs/partials/epi_main.html',
                               'data':chart_dict, 
                               'series':location_list, 
                               'start_date':dates['start'], 
                               'end_date':dates['end'], 
                               'xaxis':xaxis, 
                               'yaxis':yaxis, 
                               'chart_title': chart_title,
                               'tooltip_prefix': 'Week ', 
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                                }, context_instance=RequestContext(request))    

def birth_detail(request, location_id=None):
    """
        birth reports view
        
    """
    dates = get_dates(request)
    max_date = datetime.datetime.now()   
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]
    total = report('birth', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    boys = report('birth', attribute_keyword='gender', attribute_value='M', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    girls = report('birth', attribute_keyword='gender', attribute_value='F', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    at_home = report('birth', attribute_keyword='place', attribute_value='HOME', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    percentage_at_home = report('birth', attribute_keyword='place', attribute_value='HOME', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    at_clinic = report('birth', attribute_keyword='place', attribute_value='CLINIC', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    at_facility = report('birth', attribute_keyword='place', attribute_value='FACILITY', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    x = 0
    while x < len(percentage_at_home):
        home_divide = float(percentage_at_home[x]['value'])
        total_value = float(total[x]['value'])
        home_divide /= total_value
        percentage_at_home[x]['value'] = round(home_divide*100,1)
        x +=1
   
    report_dict = {}
    reorganize_location('total', total, report_dict)
    reorganize_location('boys', boys, report_dict)
    reorganize_location('girls', girls, report_dict)
    reorganize_location('at_home', at_home, report_dict)
    reorganize_location('at_clinic', at_clinic, report_dict)
    reorganize_location('at_facility', at_facility, report_dict)
    reorganize_location('percentage_at_home', percentage_at_home, report_dict)
    
    columns = (('','',1),
                  ('Total Births', '', 1),
                  ('Boys','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/gender/M/')"),
                  ('Girls','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/gender/F/')"),
                  ('Delivered at Home','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/place/HOME/')"),
                  ('Delivered at Clinic','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/place/CLINIC/')"),
                  ('Delivered at Facility','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/place/FACILITY/')"),
                  ('% Delivered at Home','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/place/percentage/')")
                  )
    
    chart = report('birth', location=location, start_date=dates['start'], end_date=dates['end'], group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION | GROUP_BY_YEAR)
    chart_title = 'Variation of Total Birth Reports'
    xaxis = 'Week of Year'
    yaxis = 'Number of Cases'
    chart_dict = {}
    location_list = []
    reorganize_timespan('week', chart, chart_dict, location_list)  
    
    return render_to_response("cvs/stats.html",
                              {'report':report_dict, 
                               'columns':columns,  
                               'location_id':location_id, 
                               'report_template':'cvs/partials/birth_main.html',
                               'data':chart_dict, 
                               'series':location_list, 
                               'start_date':dates['start'], 
                               'end_date':dates['end'], 
                               'xaxis':xaxis, 
                               'yaxis':yaxis, 
                               'chart_title': chart_title,
                               'tooltip_prefix': 'Week ', 
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                                }, context_instance=RequestContext(request))
    
def death_detail(request, location_id=None):
    """
        death reports view
        
    """
    dates = get_dates(request)
    max_date = datetime.datetime.now()   
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]
    total = report('death', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    boys = report('death', attribute_keyword='gender', attribute_value='M', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    girls = report('death', attribute_keyword='gender', attribute_value='F', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    under_28days = report('death', attribute_keyword='age', attribute_value={"under":(28)}, location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    upto_3months = report('death', attribute_keyword='age', attribute_value={"between":(28, 90)}, location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    upto_12months = report('death', attribute_keyword='age', attribute_value={"between":(90, 365)}, location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    upto_5years = report('death', attribute_keyword='age', attribute_value={"between":(365, 1825)}, location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    report_dict = {}
    reorganize_location('total', total, report_dict)
    reorganize_location('boys', boys, report_dict)
    reorganize_location('girls', girls, report_dict)
    reorganize_location('under_28days', under_28days, report_dict)
    reorganize_location('upto_3months', upto_3months, report_dict)
    reorganize_location('upto_12months', upto_12months, report_dict)
    reorganize_location('upto_5years', upto_5years, report_dict)
    
    columns = (('','',1),
                  ('Total Child Deaths', '', 1),
                  ('Male Deaths','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/death/gender/M/')"),
                  ('Female Deaths','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/death/gender/F/')"),
                  ('Deaths Under 28 days','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/death/age/under_28/')"),
                  ('Deaths 28 days to 3 months','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/death/age/between_28_90/')"),
                  ('Deaths 3 months to 12 months','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/death/age/between_90_365/')"),
                  ('Deaths 1 year to 5 years','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/death/age/between_365_1825/')")
                  )
    
    chart = report('death', location=location, start_date=dates['start'], end_date=dates['end'], group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION | GROUP_BY_YEAR)
    chart_title = 'Variation of Total Child Death Reports'
    xaxis = 'Week of Year'
    yaxis = 'Number of Cases'
    chart_dict = {}
    location_list = []
    reorganize_timespan('week', chart, chart_dict, location_list)  
    
    return render_to_response("cvs/stats.html",
                              {'report':report_dict, 
                               'columns':columns,  
                               'location_id':location_id, 
                               'report_template':'cvs/partials/death_main.html',
                               'data':chart_dict, 
                               'series':location_list, 
                               'start_date':dates['start'], 
                               'end_date':dates['end'], 
                               'xaxis':xaxis, 
                               'yaxis':yaxis, 
                               'chart_title': chart_title,
                               'tooltip_prefix': 'Week ', 
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                                }, context_instance=RequestContext(request))

def home_detail(request, location_id=None):
    """
        home reports view

    """
    dates = get_dates(request)
    max_date = datetime.datetime.now()
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]
    total = report('home', attribute_keyword='to', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    safe_drinking_water = report('home', attribute_keyword='wa', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    percentage_safe_drinking_water = report('home', attribute_keyword='wa', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    hand_washing_facilities = report('home', attribute_keyword='ha', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    percentage_hand_washing_facilities = report('home', attribute_keyword='ha', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    latrines = report('home', attribute_keyword='la', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    percentage_latrines = report('home', attribute_keyword='la', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    ittns = report('home', attribute_keyword='it', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
    percentage_ittns = report('home', attribute_keyword='it', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'], request=request)
        
    report_dict = {}
    reorganize_location('total', total, report_dict)
    reorganize_location('safe_drinking_water', safe_drinking_water, report_dict)
    reorganize_location('hand_washing_facilities', hand_washing_facilities, report_dict)
    reorganize_location('latrines', latrines, report_dict)
    reorganize_location('ittns', ittns, report_dict)

    percentage_dictionaries = {
                    "percentage_safe_drinking_water":percentage_safe_drinking_water,
                    "percentage_hand_washing_facilities":percentage_hand_washing_facilities,
                    "percentage_latrines":percentage_latrines,
                    "percentage_ittns":percentage_ittns
                    }

    for dictx_name, dictx in percentage_dictionaries.items():
        x = 0
        while x < len(dictx):
            dictx_divide = float(dictx[x]['value'])
            total_value = float(total[x]['value'])
            dictx_divide /= total_value
            dictx[x]['value'] = round(dictx_divide*100,1)
            x +=1
        reorganize_location(dictx_name, dictx, report_dict)

    columns = (
                  ('Total Households Visited', 'javascript:void(0)', 2,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/to/')"),
                  ('Safe Drinking Water','javascript:void(0)',2,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/wa/')"),
                  ('Hand Washing Facilities','javascript:void(0)',2,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/ha/')"),
                  ('Latrines','javascript:void(0)',2,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/la/')"),
                  ('ITTNs/LLINs','javascript:void(0)',2,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/it/')"),
                  )
    bottom_columns = (('','',2),
                    ('Total', '', 1),
                    ('% of Total', '', 1),
                    ('Total', '', 1),
                    ('% of Total', '', 1),
                    ('Total', '', 1),
                    ('% of Total', '', 1),
                    ('Total', '', 1),
                    ('% of Total', '', 1),
                )

    chart = report('home', attribute_keyword='to', location=location, start_date=dates['start'], end_date=dates['end'], group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION | GROUP_BY_YEAR)
    chart_title = 'Variation of Total Households Visited'
    xaxis = 'Week of Year'
    yaxis = 'Number of Cases'
    chart_dict = {}
    location_list = []
    reorganize_timespan('week', chart, chart_dict, location_list)

    return render_to_response("cvs/stats.html",
                              {'report':report_dict,
                               'columns':columns,
                               'bottom_columns':bottom_columns,
                               'location_id':location_id,
                               'report_template':'cvs/partials/home_main.html',
                               'data':chart_dict,
                               'series':location_list,
                               'start_date':dates['start'],
                               'end_date':dates['end'],
                               'xaxis':xaxis,
                               'yaxis':yaxis,
                               'chart_title': chart_title,
                               'tooltip_prefix': 'Week ',
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                                }, context_instance=RequestContext(request))