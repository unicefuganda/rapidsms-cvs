from healthmodels.models import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from healthmodels.models.HealthFacility import HealthFacility
from healthmodels.models.HealthProvider import HealthProvider
from simple_locations.models import AreaType,Point,Area
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect,HttpResponse
from cvs.utils import report, reorganize_timespan, GROUP_BY_LOCATION, GROUP_BY_WEEK, GROUP_BY_YEAR, GROUP_BY_DAY
import datetime

def chart(request, xform_keyword, attribute_keyword=None, location_id=None):
    print "xform %s attribute %s" % (xform_keyword, attribute_keyword)
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]    
    end_date = datetime.datetime.now()
    start_date = datetime.datetime.now() - datetime.timedelta(days=30)
    if attribute_keyword:
        chart_data = report(xform_keyword, attribute_keyword=attribute_keyword, start_date=start_date, end_date=end_date, group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
    else:
        chart_data = report(xform_keyword, start_date=start_date, end_date=end_date, group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
    report_dict = {}
    location_list = []
    reorganize_timespan('week', chart_data, report_dict, location_list)
    return render_to_response("cvs/partials/chart.html",
                              {'data':report_dict, 
                               'series':location_list, 
                               'start_date':start_date, 
                               'end_date':end_date,
                               'chart_title':'lookup title here',
                               'xaxis':'xaxis',
                               'yaxis':'yaxis',
                               'tooltip_prefix':'FIXME ' }, context_instance=RequestContext(request))