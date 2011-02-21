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
from cvs.utils import report, reorganize_timespan, get_expected_epi, get_group_by, GROUP_BY_LOCATION, GROUP_BY_WEEK, GROUP_BY_YEAR, GROUP_BY_DAY
from cvs.forms import DateRangeForm
import datetime
from django.utils.datastructures import SortedDict

def chart(request, xform_keyword, attribute_keyword=None, attribute_value=None, location_id=None,label='cases'):
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
            request.session['start_date'] = start_date
            request.session['end_date'] = end_date
        
    else:
        cursor = connection.cursor()
        cursor.execute("select max(created) from rapidsms_xforms_xformsubmission")
        end_date = cursor.fetchone()[0]
        start_date = end_date - datetime.timedelta(days=30)
        if request.session.get('start_date',None)  and request.session.get('end_date',None):
            start_date=request.session['start_date']
            end_date=request.session['end_date']

    group_by = get_group_by(start_date, end_date)
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]

    params = chart_params(xform_keyword, attribute_keyword, attribute_value)
    if attribute_keyword and attribute_value:
        if attribute_keyword.find('__') > 0:
            attribute_keyword = attribute_keyword.split('__')
        if attribute_value.find('__') > 0:
            attribute_value = attribute_value.split('__')
        if xform_keyword == 'death' and attribute_keyword == 'age':
            vlist = attribute_value.split('_')
            value_dict_key = str(vlist[0])
            value_dict_values = []
            x = 1
            while x < len(vlist):
                value_dict_values.append(int(vlist[x]))
                x +=1
            attribute_value = {value_dict_key:value_dict_values}
        if xform_keyword == 'birth' and attribute_value == 'percentage':
            label="%"
            percentage_at_home = report(xform_keyword, attribute_keyword='place', attribute_value='HOME', start_date=start_date, end_date=end_date, group_by=group_by['group_by'] | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
            total = report(xform_keyword, start_date=start_date, end_date=end_date, group_by=group_by['group_by'] | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
            x = 0
            while x < len(percentage_at_home):
                home_divide = float(percentage_at_home[x]['value'])
                total_value = float(total[x]['value'])
                home_divide /= total_value
                percentage_at_home[x]['value'] = round(home_divide*100,1)
                x +=1
            chart_data = percentage_at_home
        elif xform_keyword == 'home' and attribute_value == 'percentage':
            label="%"
            attribute_values_list = report('home', attribute_keyword=attribute_keyword, location=location, group_by = group_by['group_by'] | GROUP_BY_LOCATION | GROUP_BY_YEAR, start_date=start_date, end_date=end_date)
            home_total = report('home', attribute_keyword='to', location=location, group_by = group_by['group_by'] | GROUP_BY_LOCATION | GROUP_BY_YEAR, start_date=start_date, end_date=end_date)
            for attribute_values_dict in attribute_values_list:
                try:
                    attribute_values_dict['value']=(attribute_values_dict['value']/float(home_total[attribute_values_list.index(attribute_values_dict)]['value']))*100
                except (ZeroDivisionError, TypeError):
                    attribute_values_dict['value']='N/A'

            chart_data = attribute_values_list
        else:
            chart_data = report(xform_keyword, attribute_keyword=attribute_keyword, attribute_value=attribute_value, start_date=start_date, end_date=end_date, group_by=group_by['group_by'] | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
    elif attribute_keyword and not attribute_value:
        if xform_keyword == 'epi' and attribute_keyword == 'percentage':
            label="%"
            percentage_epi = report(xform_keyword, attribute_keyword=None, attribute_value=None, start_date=start_date, end_date=end_date, group_by=group_by['group_by'] | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
            expected_epi = get_expected_epi(location,request)
            y = 0
            while y < len(percentage_epi):
                epi_divide = float(percentage_epi[y]['value'])
                epi_divide /= expected_epi
                percentage_epi[y]['value'] = round(epi_divide*100,1)
                y +=1
            chart_data = percentage_epi
        else:
            chart_data = report(xform_keyword, attribute_keyword=attribute_keyword, start_date=start_date, end_date=end_date, group_by=group_by['group_by'] | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
    else:
        chart_data = report(xform_keyword, start_date=start_date, end_date=end_date, group_by=group_by['group_by'] | GROUP_BY_LOCATION | GROUP_BY_YEAR, location=location)
    report_dict = SortedDict()
    location_list = []
# FIXME: should also fixure out how to calculate max and min values for
# yaxis range
    reorganize_timespan(group_by['group_by_name'], chart_data, report_dict, location_list, request)
    return render_to_response("cvs/partials/chart.html",
                              {'data':report_dict, 
                               'series':location_list, 
                               'start_date':start_date, 
                               'end_date':end_date,
                               'chart_title':params['chart_title'],
                               'xaxis':params['xaxis'],
                               'yaxis':params['yaxis'],
                               'label':label,
                               }, context_instance=RequestContext(request))

def chart_params(xform_keyword, attribute_keyword, attribute_value=None):
    
    keyword_dict = {
    'ma':'Malaria',
    'tb':'Tuber Closis',
    'bd': 'Bloody Diarrhea',
    'ab':'Animal Bites',
    'af':'Polio',
    'mg':'Meningitis',
    'me':'Measles',
    'ch':'Cholera',
    'gw':'Guinea Worm',
    'nt':'Neonatal Tetanus',
    'yf':'Yellow Fever',
    'pl':'Plague',
    'ra':'Rabies',
    'vf':'Hemorrhagic Fevers',
    'ei':'Infectious Diseases',
    'to':'Total Household Visited',
    'wa':'Safe Drinking Water',
    'ha':'Hand Washing Facilites',
    'la':'Latrines',
    'it':'ITTNs/LLINs'
    }   
    value_dict = {
                  'G':'Green',
                  'G__T':'Green + Oedema',
                  'Y':'Yellow',
                  'R':'Red',
                  'R__T':'Red + Oedema',
                  'M':'Male',
                  'F':'Female',
                  'HOME':'Home',
                  'CLINIC':'Clinic',
                  'FACILITY':'Facility',
                  'percentage':'Percentage Home',
                  'under_28': 'under 28 days',
                  'between_28_90': 'between 28 days and 3 months',
                  'between_90_365': 'between 3 months and 12 months',
                  'between_365_1825': 'between 1 year and 5 years',
                  }
    
    indicator = ''
    category = ''
    yaxis = 'Number of Reports'
    xaxis = 'weeks'
    if xform_keyword == 'epi' or xform_keyword == 'home':
        yaxis = 'Percentage of Reports'
        if xform_keyword == 'epi' and attribute_keyword == 'percentage':
            indicator = 'Percentage of Expected Weekly EPI Reports Received'
        elif attribute_keyword == 'wa' and attribute_value == 'percentage':
            indicator = 'Percentage of Homesteads With Safe Drinking Water'
        else:
            yaxis = 'Number of Reports'
            indicator = keyword_dict[attribute_keyword] + " Reports"
    
    if attribute_value:
        if attribute_value == 'percentage':
            yaxis = 'Percentage of Reports'
        if xform_keyword == 'muac':
            category = value_dict[attribute_value] + " Category "
        else:
            category = value_dict[attribute_value]
                
    epi_params = {"chart_title":"Variation of "+str(indicator)+" ", "yaxis": yaxis, "xaxis":xaxis}
    muac_params = {"chart_title":"Variation of "+str(category)+" Malnutrition Reports", "yaxis": yaxis, "xaxis":xaxis}
    birth_params = {"chart_title":"Variation of "+str(category)+" Birth Reports", "yaxis": yaxis, "xaxis":xaxis}
    death_params = {"chart_title":"Variation of Death Reports for Children "+str(category)+"", "yaxis": yaxis, "xaxis":xaxis}
    home_params = {"chart_title":"Variation of "+str(indicator)+" Reports", "yaxis": yaxis, "xaxis": xaxis}

    params = {"muac":muac_params, "epi":epi_params, "birth":birth_params, "death":death_params, "home":home_params}
    
    return params[xform_keyword]
