from healthmodels.models import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from healthmodels.models.HealthFacility import HealthFacility
from healthmodels.models.HealthProvider import HealthProvider
from simple_locations.models import AreaType,Point,Area
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect,HttpResponse
from django.db import connection
from cvs.utils import report, reorganize_timespan, GROUP_BY_LOCATION, GROUP_BY_WEEK, GROUP_BY_YEAR, GROUP_BY_DAY
from cvs.forms import DateRangeForm
import datetime

def chart(request, xform_keyword, attribute_keyword=None, attribute_value=None, location_id=None):
    """
        This view can handle basic functionality for all charts.  This view
        is a partial response, to be loaded within a container div for another
        page, and can also handle post requests with a date range passed in.
        
        FIXME: grouping should be performed appropriately, as per the instructions
        in views.stats.index
        
        FIXME: I would have a static dictionary, for looking up chart titles, and
        x and y axis labels, based on the xform_keyword and attribute_keyword
        values passed in (see the FIXMEs) below.
    """
    if request.POST:
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_ts']
            end_date = form.cleaned_data['end_ts']
    else:
        cursor = connection.cursor()
        cursor.execute("select max(created) from rapidsms_xforms_xformsubmission")
        end_date = cursor.fetchone()[0]
        start_date = end_date - datetime.timedelta(days=30)
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]
        
    params = chart_params(xform_keyword, attribute_keyword, attribute_value)
    
    if attribute_keyword and attribute_value:
#        import pdb
#        pdb.set_trace()
        if attribute_keyword.find('__') > 0:
            attribute_keyword = attribute_keyword.split('__')
        if attribute_value.find('__') > 0:
            attribute_value = attribute_value.split('__')
        chart_data = report(xform_keyword, attribute_keyword=attribute_keyword, attribute_value=attribute_value, start_date=start_date, end_date=end_date, group_by=GROUP_BY_LOCATION, location=location)
    elif attribute_keyword and not attribute_value:
        chart_data = report(xform_keyword, attribute_keyword=attribute_keyword, start_date=start_date, end_date=end_date, group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
    else:
        chart_data = report(xform_keyword, start_date=start_date, end_date=end_date, group_by=GROUP_BY_WEEK | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
    report_dict = {}
    location_list = []
    reorganize_timespan('week', chart_data, report_dict, location_list)
    # FIXME: should also fixure out how to calculate max and min values for
    # yaxis range
#    Fixed title, yaxis and xaxis labels
#    import pdb
#    pdb.set_trace()
    return render_to_response("cvs/partials/chart.html",
                              {'data':report_dict, 
                               'series':location_list, 
                               'start_date':start_date, 
                               'end_date':end_date,
                               'chart_title':params['chart_title'],
                               'xaxis':params['xaxis'],
                               'yaxis':params['yaxis'],
                               'tooltip_prefix':params['tooltip_prefix'] }, context_instance=RequestContext(request))

def chart_params(xform_keyword, attribute_keyword, attribute_value=None):
    
    keyword_dict = (
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
    
    value_dict = (
                  ('G', "Green"),
                  ('G__T', "Green + Oedema"),
                  ('Y', "Yellow"),
                  ('R', "Red"),
                  ('R__T', "Red + Oedema"),
                  )
    
#    import pdb
#    pdb.set_trace()
    indicator = None
    category = None
    if xform_keyword != 'muac':
        for attrib_keyword, v in keyword_dict:
            if attrib_keyword == attribute_keyword:
                indicator = v
    
    if attribute_value:
        for attrib_key, v in value_dict:
            if attrib_key == attribute_value:
                category = v + " Category "
                
    epi_params = {"chart_title":"Variation of "+str(indicator)+" Reports", "yaxis": "Number of Reports", "xaxis":"weeks", "tooltip_prefix": "Week "}
    muac_params = {"chart_title":"Variation of "+str(category)+" Malnutrition Reports", "yaxis": "Number of Reports", "xaxis":"weeks", "tooltip_prefix": "Week "}

    params = {"muac":muac_params, "epi":epi_params}
    
    return params[xform_keyword]