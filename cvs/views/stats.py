from healthmodels.models import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from healthmodels.models.HealthFacility import HealthFacility
from healthmodels.models.HealthProvider import HealthProvider
from simple_locations.models import AreaType,Point,Area
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect,HttpResponse
from cvs.utils import report, GROUP_BY_LOCATION

def _add_value(key_attribute, value_attribute, key, report, report_dict):
    for dict in report:
        key_attribute_val = dict[key_attribute]
        report_dict.setdefault(key_attribute_val,{})
        report_dict[key_attribute_val][key] = dict[value_attribute]

def index(request, location_id=None):
    if location_id:
        location = get_object_or_404(Area, location_id)
    else:
        location = Area.tree.root_nodes()[0]
    muac = report('muac', location=location, group_by = GROUP_BY_LOCATION)
    ma = report('epi', attribute_keyword='ma', location=location, group_by = GROUP_BY_LOCATION)
    tb = report('epi', attribute_keyword='tb', location=location, group_by = GROUP_BY_LOCATION)
    bd = report('epi', attribute_keyword='bd', location=location, group_by = GROUP_BY_LOCATION)
    birth = report('birth', location=location, group_by = GROUP_BY_LOCATION)
    death = report('death', location=location, group_by = GROUP_BY_LOCATION)
    to = report('home', attribute_keyword='to', location=location, group_by = GROUP_BY_LOCATION)
    wa = report('home', attribute_keyword='wa', location=location, group_by = GROUP_BY_LOCATION)
    report_dict = {}
    _add_value('location_name', 'count', 'muac', muac, report_dict)
    _add_value('location_name', 'sum', 'ma', ma, report_dict)
    _add_value('location_name', 'sum', 'tb', tb, report_dict)
    _add_value('location_name', 'sum', 'bd', bd, report_dict)
    _add_value('location_name', 'count', 'birth', birth, report_dict)
    _add_value('location_name', 'count', 'death', death, report_dict)
    _add_value('location_name', 'sum', 'to', to, report_dict)
    _add_value('location_name', 'sum', 'wa', wa, report_dict)
    return render_to_response("cvs/stats.html",{'report':report_dict}, context_instance=RequestContext(request))

    