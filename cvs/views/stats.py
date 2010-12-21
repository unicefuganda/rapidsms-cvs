from healthmodels.models import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from healthmodels.models.HealthFacility import HealthFacility
from healthmodels.models.HealthProvider import HealthProvider
from simple_locations.models import AreaType,Point,Area
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect,HttpResponse
from cvs.utils import report

def index(request, location_id=None):
    if location_id:
        location = get_object_or_404(Area, location_id)
    else:
        location = Area.tree.root_nodes()[0]
    muac = report('muac', location=location)
    ma = report('epi', attribute_keyword='ma', location=location)
    tb = report('epi', attribute_keyword='tb', location=location)
    bd = report('epi', attribute_keyword='bd', location=location)
    birth = report('birth', location=location)
    death = report('death', location=location)
    to = report('home', attribute_keyword='to', location=location)
    wa = report('home', attribute_keyword='wa', location=location)
    
            
        

    