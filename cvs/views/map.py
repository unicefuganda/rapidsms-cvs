#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4


import datetime
import time

from cvs.views.dates import get_dates
from cvs.forms import DateRangeForm
from cvs.settings import MAP_KEY, MIN_LAT, MAX_LAT, MIN_LON, MAX_LON
from cvs.utils import total_submissions_by_facility, total_attribute_by_facility

from django.http import HttpResponse
from django.conf import settings
from django.utils import simplejson

from healthmodels.models.HealthFacility import HealthFacility


class JsonResponse(HttpResponse):
    """ return json content type   """

    def __init__(self, obj):
        self.original_obj = obj
        HttpResponse.__init__(self, self.serialize())
        self['Content-Type'] = 'text/javascript'

    def serialize(self):
        return simplejson.dumps(self.original_obj)


TITLE_DICT = {
    'epi_ma':'Malaria',
    'epi_tb':'Tuberclosis',
    'epi_bd': 'Bloody Diarrhea',
    'epi_ab':'Animal Bites',
    'epi_af':'Polio',
    'epi_mg':'Meningitis',
    'epi_me':'Measles',
    'epi_ch':'Cholera',
    'epi_gw':'Guinea Worm',
    'epi_nt':'Neonatal Tetanus',
    'epi_yf':'Yellow Fever',
    'epi_pl':'Plague',
    'epi_ra':'Rabies',
    'epi_vf':'Hemorrhagic Fevers',
    'epi_ei':'Infectious Diseases',
    'epi_to':'Total Household Visited',
    'epi_wa':'Safe Drinking Water',
    'epi_ha':'Hand Washing Facilites',
    'epi_la':'Latrines',
    'epi_it':'ITTNs/LLINs',
    'epi':'Total Epi Reports',
    'home':'Total Home Reports',
    'muac':'Cases of Malnutrition',
    'death':'Total Deaths',
    'birth':'Total Births',
}

def map_other_api(request, start_date, end_date):
    start_date=datetime.datetime.fromtimestamp(int(start_date))
    end_date=datetime.datetime.fromtimestamp(int(end_date))

    to_ret_data = {}
    for att in ['me','ab','af','yf','ch','gw','mg','nt','pl','rb']:
        data = total_attribute_by_facility('epi_%s'%att, start_date, end_date, (MIN_LAT, MIN_LON, MAX_LAT, MAX_LON))
        for d in data:
            id = d.pop('facility_id')
            to_ret_data.setdefault(id,\
                {'location_id':id,\
                 'location_name':"%s %s" % (d.pop('facility_name'), d.pop('type').upper()),\
                 'lat':'%.5f' % float(d.pop('latitude')),
                 'lon':'%.5f' % float(d.pop('longitude')),
                 'description':'',
                 'value':0})
            to_ret_data[id]['description'] += "%s : %d<br/>" % (TITLE_DICT["epi_%s"%att], d['value'])
            to_ret_data[id]['value'] += d['value']

    json_response_data = {'layer_title':'Other Diseases','layer_type':'flat', 'data':list(to_ret_data.values())}
    return JsonResponse(json_response_data)

def map_api(request, start_date, end_date, xform_keyword, attribute_keyword=None):
    start_date=datetime.datetime.fromtimestamp(int(start_date))
    end_date=datetime.datetime.fromtimestamp(int(end_date))

    if attribute_keyword:
        data_function = total_attribute_by_facility
        keyword = "%s_%s" % (xform_keyword, attribute_keyword)
    else:
        data_function = total_submissions_by_facility
        keyword = xform_keyword

    title = TITLE_DICT[keyword]
    data = data_function(keyword, start_date, end_date, (MIN_LAT, MIN_LON, MAX_LAT, MAX_LON))
    for d in data:
        d['lat'] = '%.5f' % float(d.pop('latitude'))
        d['lon'] = '%.5f' % float(d.pop('longitude'))
        d['location_id'] = d.pop('facility_id')
        d['location_name'] = "%s %s" % (d.pop('facility_name'), d.pop('type').upper())

    json_response_data = {'layer_title':title,'layer_type':'flat', 'data':list(data)}
    return JsonResponse(json_response_data)

def health_facility_api(request):
    data = list(HealthFacility.objects.exclude(location=None).values('location__latitude','location__longitude','pk','name','type__name'))
    icons_lookup = {
        'dho':'d',
        'hcii':'2',
        'ministry':'M',
        'hospital':'H',
        'hciv':'4',
        'hciii':'3',
    }
    icon_root = str(settings.MEDIA_URL) + 'cvs/icons/' 
    facility_icons={
        'd':icon_root + 'HOSPITAL.png',
        '2':icon_root + 'HCII.png',
        '3':icon_root + 'HCIII.png',
        '4':icon_root + 'HCIV.png',
        'H':icon_root + 'HOSPITAL.png',
        'M':icon_root + 'HOSPITAL.png',
    }

    for d in data:
        d['lat'] = '%.5f' % float(d.pop('location__latitude'))
        d['lon'] = '%.5f' % float(d.pop('location__longitude'))
        d['location_id'] = d.pop('pk')
        type = d.pop('type__name')
        d['location_name'] = "%s %s" % (d.pop('name'), type.upper())
        d['icon'] = icons_lookup[type]
    json_response_data = {'layer_title':'Health Facility',
                          'layer_type':'marker',
                          'data':data,
                          'icons':facility_icons}
    return JsonResponse(json_response_data)

