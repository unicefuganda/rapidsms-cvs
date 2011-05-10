from healthmodels.models import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from healthmodels.models.HealthFacility import HealthFacility
from healthmodels.models.HealthProvider import HealthProvider
from simple_locations.models import AreaType,Point,Area
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect,HttpResponse
from cvs.utils import total_submissions,total_attribute_value,registered_reporters, reorganize_location, reorganize_timespan, get_dates, get_expected_epi, GROUP_BY_WEEK,GROUP_BY_MONTH,GROUP_BY_DAY,GROUP_BY_QUARTER,get_group_by,ExcelResponse
from cvs.forms import DateRangeForm
import datetime
import time
from django.utils.datastructures import SortedDict
from rapidsms_xforms.models import XFormSubmission, XFormSubmissionValue
from rapidsms.models import Contact
import re
from django.utils.safestring import mark_safe
from django.db.models import Count,Sum

Num_REG=re.compile('\d+')

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
    chart=request.session.get('stats',None)
    if chart :

        chart_path=Num_REG.sub(str(location.pk),chart).rsplit("?")[0]+"?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) )
        request.session['stats']=chart_path
    else:
        request.session['stats']=mark_safe("/cvs/charts/"+str(location.pk)+"/muac/?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) ))
    start_date = dates['start']
    end_date = dates['end']
    muac = total_submissions('muac', start_date, end_date, location)
    ma = total_attribute_value('epi_ma', start_date, end_date, location)
    tb = total_attribute_value('epi_tb', start_date, end_date, location)
    bd = total_attribute_value('epi_bd', start_date, end_date, location)
    birth = total_submissions('birth', start_date, end_date, location)
    death = total_submissions('death', start_date, end_date, location)
    percentage_safe_water = total_attribute_value('home_wa', start_date, end_date, location)
    home_total = total_attribute_value('home_to', start_date, end_date, location)
    percentage_epi = total_submissions('muac', start_date, end_date, location)
    active_lower_bound=datetime.datetime.now()
    active_upper_bound=datetime.datetime.now()-datetime.timedelta(days=14)
    activeReporters = total_submissions(None, active_upper_bound,active_lower_bound, location,type='active_reporters')
    registeredReporters = registered_reporters(location)

    expected_epi = get_expected_epi(location,request)

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
    reorganize_location('home_total', home_total, report_dict)
    reorganize_location('activeReporters', activeReporters, report_dict)
    reorganize_location('registeredReporters', registeredReporters, report_dict)
    for loc, val_dict in report_dict.iteritems():
        if 'home_total' in val_dict and 'percentage_safe_water' in val_dict:
            home_total = float(val_dict['home_total'])
            percentage_safe_water = float(val_dict['percentage_safe_water'])
            val_dict['percentage_safe_water'] = round(((percentage_safe_water / home_total)*100), 1)
        else:
            val_dict['percentage_safe_water'] = 'N/A'

    # label, link, colspan
    topColumns = (('','',1),
                  ('Malnutrition', '/cvs/muac/?root=true', 1),
                  ('Epi','/cvs/epi/?root=true',3),
                  ('Birth','/cvs/birth/?root=true',1),
                  ('Death','/cvs/death/?root=true',1),
                  ('Home', '/cvs/home/?root=true',1),
                  ('Reporters','/cvs/reporter/',2)
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
               #('% of expected weekly Epi reports received','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/percentage/')"),
               ('Active Reporters','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "chart/" + str(location.pk) + "/active_reporters/')"),
               ('Registered Reporters','',1),
    )

    return render_to_response("cvs/stats.html",
                              {'report':report_dict,
                               'top_columns':topColumns,
                               'columns':columns,
                               'location_id':location_id,
                               'report_template':'cvs/partials/stats_main.html',
                               'start_date':dates['start'],
                               'end_date':dates['end'],
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                               'page':'stats',
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
    module = request.GET.get('module', False)
    if not module:
        chart=request.session.get('muac',None)
        if chart :
            chart_path=Num_REG.sub(str(location.pk),chart).rsplit("?")[0]+"?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) )
            request.session['muac']=chart_path
        else:
            request.session['muac']=mark_safe("/cvs/charts/"+str(location.pk)+"/muac/?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) ))
    start_date = dates['start']
    end_date = dates['end']
    total = total_submissions('muac', start_date, end_date, location)
    green = total_submissions('muac', start_date, end_date, location, {
                'eav__muac_category':'G',
            })
    green_oedema = total_submissions('muac', start_date, end_date, location, {
                'eav__muac_category':'G',
                'eav__muac_ignored':'T',
            })
    yellow = total_submissions('muac', start_date, end_date, location, {
                'eav__muac_category':'Y',
            })
    red = total_submissions('muac', start_date, end_date, location, {
                'eav__muac_category':'R',
            })
    red_oedema = total_submissions('muac', start_date, end_date, location, {
                'eav__muac_category':'R',
                'eav__muac_ignored':'T',
            })

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
                  ('Green+oe','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/category__ignored/G__T/')"),
                  ('Yellow','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/category/Y/')"),
                  ('Red','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/category/R/')"),
                  ('Red+oe','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/muac/category__ignored/R__T/')")
                  )

    stats_template = "cvs/stats_module.html" if module else "cvs/stats.html"
    return render_to_response(stats_template,
                              {'report':report_dict,
                               'columns':columns,
                               'location_id':location_id,
                               'report_template':'cvs/partials/muac_main.html',
                               'start_date':dates['start'],
                               'end_date':dates['end'],
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                               'page':'muac',
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
    module = request.GET.get('module', False)
    if not module:
        chart=request.session.get('epi',None)
        if chart:
            chart_path=Num_REG.sub(str(location.pk),chart).rsplit("?")[0]+"?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) )
            request.session['epi']=chart_path
        else:
            request.session['epi']=mark_safe("/cvs/charts/"+str(location.pk)+"/epi/ma/?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) ))

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
    start_date=dates['start']
    end_date=dates['end']
    total = total_submissions('epi', start_date, end_date, location)
#    total = report('epi', location=location, group_by = GROUP_BY_LOCATION, start_date=dates['start'], end_date=dates['end'],request=request)
    reorganize_location('total', total, report_dict)
    for attrib_keyword, v in categories:
        dictx = total_attribute_value('epi_%s' % attrib_keyword, start_date, end_date, location)
        reorganize_location(attrib_keyword, dictx, report_dict)

    columns = [
        ('','',1),
        ('Total','javascript:void(0)',1, "loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/')")
    ]
    for k, v in categories:
        link = 'javascript:void(0)'
        colspan = 1
        onclick = "loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/epi/"+k+"/')"
        tup = (v, link, colspan, onclick)
        columns.append(tup)

    stats_template = "cvs/stats_module.html" if module else "cvs/stats.html"
    return render_to_response(stats_template,
                              {'report':report_dict,
                               'columns':columns,
                               'location_id':location_id,
                               'report_template':'cvs/partials/epi_main.html',
                               'start_date':dates['start'],
                               'end_date':dates['end'],
                               'module':module,
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                               'page':'epi',
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
    module = request.GET.get('module', False)
    if not module:
        chart=request.session.get('birth',None)
        if chart :
            chart_path=Num_REG.sub(str(location.pk),chart).rsplit("?")[0]+"?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) )
            request.session['birth']=chart_path
        else:
            request.session['birth']=mark_safe("/cvs/charts/"+str(location.pk)+"/birth/?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) ))
    start_date=dates['start']
    end_date=dates['end']
    total = total_submissions('birth', start_date, end_date, location)
    boys = total_submissions('birth', start_date, end_date, location, {
                'eav__birth_gender':'M',
            })
    girls = total_submissions('birth', start_date, end_date, location, {
                'eav__birth_gender':'F',
            })
    at_home = total_submissions('birth', start_date, end_date, location, {
                'eav__birth_place':'HOME',
            })
    percentage_at_home = total_submissions('birth', start_date, end_date, location, {
                'eav__birth_place':'HOME',
            })
    at_facility = total_submissions('birth', start_date, end_date, location, {
                'eav__birth_place':'FACILITY',
            })
    percentage_at_facility = total_submissions('birth', start_date, end_date, location, {
                'eav__birth_place':'FACILITY',
            })

    report_dict = {}
    reorganize_location('total', total, report_dict)
    reorganize_location('boys', boys, report_dict)
    reorganize_location('girls', girls, report_dict)
    reorganize_location('at_home', at_home, report_dict)
    reorganize_location('at_facility', at_facility, report_dict)
    reorganize_location('percentage_at_home', percentage_at_home, report_dict)
    reorganize_location('percentage_at_facility', percentage_at_facility, report_dict)
    for loc, val_dict in report_dict.iteritems():
        if 'total' in val_dict and 'percentage_at_home' in val_dict:
            total = float(val_dict['total'])
            percentage_at_home = float(val_dict['percentage_at_home'])
            val_dict['percentage_at_home'] = round(((percentage_at_home / total)*100), 1)
        else:
            val_dict['percentage_at_home'] = 'N/A'

    for loc, val_dict in report_dict.iteritems():
        if 'total' in val_dict and 'percentage_at_facility' in val_dict:
            total = float(val_dict['total'])
            percentage_at_facility = float(val_dict['percentage_at_facility'])
            val_dict['percentage_at_facility'] = round(((percentage_at_facility / total)*100), 1)
        else:
            val_dict['percentage_at_facility'] = 'N/A'

    columns = (('','',1),
                  ('Total Births', '', 1),
                  ('Boys','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/gender/M/')"),
                  ('Girls','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/gender/F/')"),
                  ('Delivered at Home','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/place/HOME/')"),
                  ('Delivered at Facility','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/place/FACILITY/')"),
                  ('% Delivered at Home','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/place/HOME/percentage/')"),
                  ('% Delivered at Facility','javascript:void(0)',1,"loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/birth/place/FACILITY/percentage/')")
                  )

    stats_template = "cvs/stats_module.html" if module else "cvs/stats.html"
    return render_to_response(stats_template,
                              {'report':report_dict,
                               'columns':columns,
                               'location_id':location_id,
                               'report_template':'cvs/partials/birth_main.html',
                               'start_date':dates['start'],
                               'end_date':dates['end'],
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                               'page':'birth',
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
    module = request.GET.get('module', False)
    if not module:
        chart=request.session.get('death',None)
        if chart :
            chart_path=Num_REG.sub(str(location.pk),chart).rsplit("?")[0]+"?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) )
            request.session['death']=chart_path
        else:
            request.session['death']=mark_safe("/cvs/charts/"+str(location.pk)+"/death/?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) ))
    start_date=dates['start']
    end_date=dates['end']
    total = total_submissions('death', start_date, end_date, location)
    boys = total_submissions('death', start_date, end_date, location, {
                'eav__death_gender':'M',
            })
    girls = total_submissions('death', start_date, end_date, location, {
                'eav__death_gender':'F',
            })
    under_28days = total_submissions('death', start_date, end_date, location, {
                'eav__death_age__lt':28,
            })
    upto_3months = total_submissions('death', start_date, end_date, location, {
                'eav__death_age__range':(28,90)
            })
    upto_12months = total_submissions('death', start_date, end_date, location, {
                'eav__death_age__range':(90,365)
            })
    upto_5years = total_submissions('death', start_date, end_date, location, {
                'eav__death_age__range':(365,1825)
            })

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

    stats_template = "cvs/stats_module.html" if module else "cvs/stats.html"
    return render_to_response(stats_template,
                              {'report':report_dict,
                               'columns':columns,
                               'location_id':location_id,
                               'report_template':'cvs/partials/death_main.html',
                               'start_date':dates['start'],
                               'end_date':dates['end'],
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                               'page':'death',
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
    module = request.GET.get('module', False)
    if not module:
        chart=request.session.get('home',None)
        if chart:
            chart_path=Num_REG.sub(str(location.pk),chart).rsplit("?")[0]+"?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()) ,time.mktime(dates['end'].timetuple()) )
            request.session['home']=chart_path
        else:
            request.session['home']="/cvs/charts/"+str(location.pk)+"/home/to/?start_date=%d&end_date=%d"%(time.mktime(dates['start'].timetuple()),time.mktime(dates['end'].timetuple()) )
    start_date=dates['start']
    end_date=dates['end']
    total_reports = total_submissions('home', start_date, end_date, location)
    total = total_attribute_value('home_to', start_date, end_date, location)
    safe_drinking_water = total_attribute_value('home_wa', start_date, end_date, location)
    percentage_safe_drinking_water = total_attribute_value('home_wa', start_date, end_date, location)
    hand_washing_facilities = total_attribute_value('home_ha', start_date, end_date, location)
    percentage_hand_washing_facilities = total_attribute_value('home_ha', start_date, end_date, location)
    latrines = total_attribute_value('home_la', start_date, end_date, location)
    percentage_latrines = total_attribute_value('home_la', start_date, end_date, location)
    ittns = total_attribute_value('home_it', start_date, end_date, location)
    percentage_ittns = total_attribute_value('home_it', start_date, end_date, location)

    report_dict = {}
    reorganize_location('total_reports', total_reports, report_dict)
    reorganize_location('total', total, report_dict)
    reorganize_location('safe_drinking_water', safe_drinking_water, report_dict)
    reorganize_location('hand_washing_facilities', hand_washing_facilities, report_dict)
    reorganize_location('latrines', latrines, report_dict)
    reorganize_location('ittns', ittns, report_dict)
    reorganize_location('percentage_safe_drinking_water', percentage_safe_drinking_water, report_dict)
    reorganize_location('percentage_hand_washing_facilities', percentage_hand_washing_facilities, report_dict)
    reorganize_location('percentage_latrines', percentage_latrines, report_dict)
    reorganize_location('percentage_ittns', percentage_ittns, report_dict)

    percentage_dictionaries = {
                    "percentage_safe_drinking_water":percentage_safe_drinking_water,
                    "percentage_hand_washing_facilities":percentage_hand_washing_facilities,
                    "percentage_latrines":percentage_latrines,
                    "percentage_ittns":percentage_ittns,
                    }

    for dictx_name, dictx in percentage_dictionaries.items():
        for loc, val_dict in report_dict.iteritems():
            if 'total' in val_dict and str(dictx_name) in val_dict:
                total = float(val_dict['total'])
                percentage_divisor = float(val_dict.get(dictx_name))
                val_dict[dictx_name] = round(((percentage_divisor / total)*100), 1)
            else:
                val_dict[dictx_name] = 'N/A'

    columns = (
        ('', '', 3),
        ('Safe Drinking Water','',2),
        ('Hand Washing Facilities','',2),
        ('Latrines','',2),
        ('ITTNs/LLINs','',2),
    )
    bottom_columns = (
        ('','',1),
        ('Total Reports', "javascript:loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/')", 1),
        ('Total Households Visited', "javascript:loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/to/')", 1),
        ('Total', '', 1),
        ("% of Total", "javascript:loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/wa/percentage/')", 1,""),
        ('Total', '', 1),
        ('% of Total', "javascript:loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/ha/percentage/')", 1),
        ('Total', '', 1),
        ('% of Total', "javascript:loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/la/percentage/')", 1),
        ('Total', '', 1),
        ('% of Total', "javascript:loadChart('../" + ("../" if location_id else "") + "charts/" + str(location.pk) + "/home/it/percentage/')", 1,),
    )

    stats_template = "cvs/stats_module.html" if module else "cvs/stats.html"
    return render_to_response(stats_template,
                              {'report':report_dict,
                               'columns':columns,
                               'bottom_columns':bottom_columns,
                               'location_id':location_id,
                               'report_template':'cvs/partials/home_main.html',
                               'start_date':dates['start'],
                               'end_date':dates['end'],
                               # timestamps in python are in seconds,
                               # in javascript they're in milliseconds
                               'max_ts':time.mktime(max_date.timetuple()) * 1000,
                               'min_ts':time.mktime(dates['min'].timetuple()) * 1000,
                               'start_ts':time.mktime(dates['start'].timetuple()) * 1000,
                               'end_ts':time.mktime(dates['end'].timetuple()) * 1000,
                               'date_range_form':dates['form'],
                               'page':'home',
                                }, context_instance=RequestContext(request))


def get_district(lst,lft,rght):
    "get a district name give a location's rght and lft"
    for d in lst:
        if d[1][0] <=lft and d[1][1] >=rght:
            return d[0]


def export_as_excel(request):
    submissions =XFormSubmission.objects.select_related('connection','connection__identity','connection__contact','connection__contact__name').all()
    health_providers=HealthProvider.objects.select_related('location','facility','location__name','facility__name','location__lft','loction__rght')
    export_data_list=[]
    districts=[]
    for d in Area.objects.filter(kind__slug='district'):
        districts.append((d.name,[d.lft,d.rght]))
    for submission in submissions:
        export_data=SortedDict()
        if submission.connection.contact:
            export_data['reporter_name']=submission.connection.contact.name
        else:
            export_data['reporter_name']=''

        export_data['reporter_number']=submission.connection.identity
        if submission.connection.contact:
            try:
                loc=health_providers.filter(contact_ptr=submission.connection.contact.pk)[0].location
                export_data['location']=loc.name
                export_data['district']=get_district(districts,loc.lft,loc.rght)
            except:
                export_data['location']=''
                export_data['district']=''
        else:
             export_data['location']=''
             export_data['district']=''

        export_data['time']=str(submission.created)
        if submission.connection.contact :
            try:
                export_data['facility']=health_providers.filter(contact_ptr=submission.connection.contact)[0].facility.name
            except:
                export_data['facility']=''

        else:
            export_data['facility']=''
        export_data['message']=submission.raw
        data={}
        for d in submission.values.all():
            data[d.attribute.slug]=d.value
        export_data['report_keyword']=submission.xform.keyword
        export_data['muac_name']=data.get('muac_name','')
        export_data['muac_gender']=data.get('muac_gender','')
        export_data['muac_age']=data.get('muac_age','')
        export_data['muac_category']=data.get('muac_category','')
        export_data['muac_eodema']=data.get('muac_eodema','')
        export_data['home_it']=data.get('home_it','')
        export_data['home_to']=data.get('home_to','')
        export_data['home_la']=data.get('home_la','')
        export_data['home_ha']=data.get('home_ha','')
        export_data['home_wa']=data.get('home_wa','')
        export_data['death_name']=data.get('death_name','')
        export_data['death_gender']=data.get('death_gender','')
        export_data['death_age']=data.get('death_age','')
        export_data['birth_name']=data.get('birth_name','')
        export_data['birth_place']=data.get('birth_place','')
        export_data['birth_gender']=data.get('birth_gender','')
        export_data['epi_ma']=data.get('epi_ma','')
        export_data['epi_bd']=data.get('epi_bd','')
        export_data['epi_tb']=data.get('epi_tb','')
        export_data['epi_ab']=data.get('epi_ab','')
        export_data['epi_af']=data.get('epi_af','')
        export_data['epi_mg']=data.get('epi_mg','')
        export_data['epi_me']=data.get('epi_me','')
        export_data['epi_ch']=data.get('epi_ch','')
        export_data['epi_gw']=data.get('epi_gw','')
        export_data['epi_nt']=data.get('epi_nt','')
        export_data['epi_yf']=data.get('epi_yf','')
        export_data['epi_pl']=data.get('epi_pl','')
        export_data['epi_ra']=data.get('epi_ra','')
        export_data['epi_vf']=data.get('epi_vf','')
        export_data['epi_ei']=data.get('epi_ei','')
        export_data_list.append(export_data)

    return ExcelResponse(export_data_list)

def module_stats(request, view_name, location_id):
    return globals()[str(view_name)](request, location_id)

