from healthmodels.models import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from healthmodels.models.HealthFacility import HealthFacility
from healthmodels.models.HealthProvider import HealthProvider
from rapidsms.contrib.locations.models import Location
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect, HttpResponse
from django.db import connection
from cvs.utils import total_submissions, active_reporters, total_attribute_value, reorganize_timespan, get_group_by, GROUP_BY_WEEK, GROUP_BY_DAY, reorganize_for_chart_api
from cvs.forms import DateRangeForm
import datetime
from django.utils.datastructures import SortedDict
from cvs.views.dates import get_dates, get_expected_epi
from rapidsms_xforms.models import XForm, XFormField
from django.utils import simplejson
from uganda_common.utils import total_submissions as total_submissions_api, total_attribute_value as total_attribute_value_api

class JsonResponse(HttpResponse):
    """ return json content type   """

    def __init__(self, obj):
        self.original_obj = obj
        HttpResponse.__init__(self, self.serialize())
        self['Content-Type'] = 'text/javascript'

    def serialize(self):
        return simplejson.dumps(self.original_obj)

def active_reporters_chart(request, location_id=None, start_date=None, end_date=None):


    if request.GET.get('module'):
        template = "cvs/partials/chart_module.html"
    dates = get_dates(request)
    start_date = dates.get('start')
    end_date = dates.get('end')

    if location_id:
        location = get_object_or_404(Location, pk=location_id)
    else:
        location = Location.tree.root_nodes()[0]
    if not location.get_children():
        return HttpResponse(status=400)

    group_by = get_group_by(start_date, end_date)

    chart_data = active_reporters(
           start_date, end_date, location,
           group_by_timespan=group_by['group_by'],
        )
    report_dict = SortedDict()
    location_list = []
    chart_data = list(chart_data)
    reorganize_timespan(group_by['group_by_name'], chart_data, report_dict, location_list, request)
    return render_to_response('cvs/partials/chart.html',
                          {'data':report_dict,
                           'series':location_list,
                           'start_date':start_date,
                           'end_date':end_date,
                           'chart_title':'Variation of Reporters',
                           'xaxis':"",
                           'yaxis':"Number",
                           'label':'reporters',
                           'timespan': group_by['group_by_name'],
                           }, context_instance=RequestContext(request))
def chart(request, xform_keyword=None, attribute_keyword=None, attribute_value=None, extra_param=None, location_id=None, label='cases', template='cvs/partials/chart.html', start_date=None, end_date=None):
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
    get_object_or_404(XForm, keyword=xform_keyword)
    if attribute_keyword:
        for attrib_keyword in attribute_keyword.split('__'):
            get_object_or_404(XFormField, slug="%s_%s" % (xform_keyword, attrib_keyword))

    if  request.environ.get('HTTP_REFERER', None):
        request.session['stats'] = request.path
    else:
        if xform_keyword:
            request.session[xform_keyword] = request.path

    if request.GET.get('module'):
        template = "cvs/partials/chart_module.html"
    dates = get_dates(request)
    start_date = dates.get('start')
    end_date = dates.get('end')

    group_by = get_group_by(start_date, end_date)
    if location_id:
        location = get_object_or_404(Location, pk=location_id)
    else:
        location = Location.tree.root_nodes()[0]

    if not location.get_children():
        return HttpResponse(status=400)

    if xform_keyword:
        params = chart_params(xform_keyword, attribute_keyword, attribute_value)
    else:
        params = {'chart_title':title, 'xaxis':'', 'yaxis':''}

    if attribute_keyword and attribute_value:
        if attribute_keyword.find('__') > 0:
            attribute_keyword = attribute_keyword.split('__')
        if attribute_value.find('__') > 0:
            attribute_value = attribute_value.split('__')
        if xform_keyword == 'death' and attribute_keyword == 'age':
            age_filter_dict = {
                'under_28':{'eav__death_age__lt':28},
                'between_28_90':{'eav__death_age__range':(28, 90)},
                'between_90_365':{'eav__death_age__range':(90, 365)},
                'between_365_1825':{'eav__death_age__range':(365, 1825)},
            }
            chart_data = total_submissions(
                xform_keyword, start_date, end_date, location,
                extra_filters=age_filter_dict[attribute_value],
                group_by_timespan=group_by['group_by'],
            )
        elif xform_keyword == 'birth' and extra_param == 'percentage':
            label = "%"
            percentage_values = total_submissions(
                xform_keyword, start_date, end_date, location,
                extra_filters={'eav__%s_%s' % (xform_keyword, attribute_keyword):attribute_value},
                group_by_timespan=group_by['group_by'])
            total = total_submissions(xform_keyword, start_date, end_date, location, group_by_timespan=group_by['group_by'])
            percentage_values = get_percentages(percentage_values, total, group_by, 'birth')
            chart_data = percentage_values
        elif xform_keyword == 'home' and attribute_value == 'percentage':
            label = "%"
            attribute_values_list = total_attribute_value('home_%s' % attribute_keyword, start_date, end_date, location, group_by_timespan=group_by['group_by'])
            home_total = total_attribute_value('home_to', start_date, end_date, location, group_by_timespan=group_by['group_by'])
            attribute_values_list = get_percentages(attribute_values_list, home_total, group_by, 'home')
            chart_data = attribute_values_list
        else:
            extra_filters = {}
            if not (type(attribute_keyword) == list):
                attribute_keyword = [attribute_keyword, ]
                attribute_value = [attribute_value, ]
            for i in range(0, len(attribute_keyword)):
                extra_filters.update({'eav__%s_%s' % (xform_keyword, attribute_keyword[i]):attribute_value[i]})
            chart_data = total_submissions(
                xform_keyword, start_date, end_date, location,
                extra_filters=extra_filters,
                group_by_timespan=group_by['group_by']
            )
    elif attribute_keyword and not attribute_value:
        if xform_keyword == 'epi' and attribute_keyword == 'percentage':
            label = "%"
            percentage_epi = total_submissions(xform_keyword, start_date, end_date, location, group_by_timespan=group_by['group_by'])
            expected_epi = get_expected_epi(location, request)
            y = 0
            while y < len(percentage_epi):
                epi_divide = float(percentage_epi[y]['value'])
                epi_divide /= expected_epi
                percentage_epi[y]['value'] = round((epi_divide * 100), 1)
                y += 1
            chart_data = percentage_epi
        else:
            chart_data = total_attribute_value(
                '%s_%s' % (xform_keyword, attribute_keyword),
                start_date, end_date, location, group_by_timespan=group_by['group_by']
            )
    else:

        chart_data = total_submissions(
           xform_keyword, start_date, end_date, location,
           group_by_timespan=group_by['group_by'],
        )
    report_dict = SortedDict()
    location_list = []
# FIXME: should also fixure out how to calculate max and min values for
# yaxis range
    chart_data = list(chart_data)
    reorganize_timespan(group_by['group_by_name'], chart_data, report_dict, location_list, request)

    return render_to_response(template,
                              {'data':report_dict,
                               'series':location_list,
                               'start_date':start_date,
                               'end_date':end_date,
                               'chart_title':params['chart_title'],
                               'xaxis':params['xaxis'],
                               'yaxis':params['yaxis'],
                               'label':label,
                               'timespan': group_by['group_by_name'],
                               }, context_instance=RequestContext(request))

def chart_params(xform_keyword, attribute_keyword, attribute_value=None):

    keyword_dict = {
    'ma':'Malaria',
    'tb':'Tuberclosis',
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
    'it':'ITTNs/LLINs',
    'epi':'Total Epi',
    'home':'Total Home',
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
            indicator = keyword_dict[(attribute_keyword or xform_keyword)] + " Reports"

    if attribute_value:
        if attribute_value == 'percentage':
            yaxis = 'Percentage of Reports'
        if xform_keyword == 'muac':
            category = value_dict[attribute_value] + " Category "
        else:
            category = value_dict[attribute_value]

    epi_params = {"chart_title":"Variation of " + str(indicator) + " ", "yaxis": yaxis, "xaxis":xaxis}
    muac_params = {"chart_title":"Variation of " + str(category) + " Malnutrition Reports", "yaxis": yaxis, "xaxis":xaxis}
    birth_params = {"chart_title":"Variation of " + str(category) + " Birth Reports", "yaxis": yaxis, "xaxis":xaxis}
    death_params = {"chart_title":"Variation of Death Reports for Children " + str(category) + "", "yaxis": yaxis, "xaxis":xaxis}
    home_params = {"chart_title":"Variation of " + str(indicator) + " Reports", "yaxis": yaxis, "xaxis": xaxis}

    params = {"muac":muac_params, "epi":epi_params, "birth":birth_params, "death":death_params, "home":home_params}

    return params[xform_keyword]

def get_percentages(percentage_values, totals, group_by, section):
    new_values = []
    for dictx  in percentage_values:
        percentage_divisor = float(dictx['value'])
        lid = dictx.get('location_id')
        date = (group_by.get('group_by_name'), dictx.get(group_by.get('group_by_name')), dictx.get('year'))
        total_value = get_divider(lid, date, totals)
        percentage_divisor /= total_value
        dictx['value'] = round(percentage_divisor * 100, 1)
        new_values.append(dictx)
    return new_values

def get_divider(lid, date, totals):
    for total in totals:
        if total.get('location_id') == lid and total.get(date[0]) == date[1] and total.get('year') == date[2]:
            return float(total.get('value'))

def chart_api(req, start_date, end_date, location_id, xform_keyword, attribute_keyword=None):
    start_date = datetime.datetime.fromtimestamp(int(start_date))
    end_date = datetime.datetime.fromtimestamp(int(end_date))
    location = get_object_or_404(Location, pk=location_id)
    if attribute_keyword:
        data_function = total_attribute_value_api
        keyword = "%s_%s" % (xform_keyword, attribute_keyword)
    else:
        data_function = total_submissions_api
        keyword = xform_keyword

    group_by = get_group_by(start_date, end_date)

    data = data_function(keyword, start_date, end_date, location, group_by_timespan=group_by['group_by'])

    chart_data = list(data)
    chart_data = reorganize_for_chart_api(group_by['group_by_name'], chart_data)
    json_response_data = {'series':list(chart_data)}
    return JsonResponse(json_response_data)


