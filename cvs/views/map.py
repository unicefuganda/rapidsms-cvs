import datetime
import time
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.safestring import mark_safe
from django.utils import simplejson
from django.http import HttpResponse
from django.db import connection
from django.conf import settings
from cvs.utils import get_dates

from healthmodels.models.HealthFacility import HealthFacility
from cvs.settings import MAP_KEY, MAP_LAYERS, MIN_LAT, MAX_LAT, MIN_LON, MAX_LON, BASELAYER

from cvs.utils import report,GROUP_BY_FACILITY

def get_dates():
    cursor = connection.cursor()
    cursor.execute("select min(created), max(created) from rapidsms_xforms_xformsubmission")
    min_date, end_date = cursor.fetchone()
    start_date = end_date - datetime.timedelta(days=300)
    start_date=time.mktime(start_date.timetuple()) * 1000
    end_date=time.mktime(end_date.timetuple()) * 1000
    max_date =  time.mktime(datetime.datetime.now().timetuple()) * 1000
    min_date=time.mktime(min_date.timetuple()) * 1000

    return (start_date, end_date, min_date, max_date)

def map_index(request):
    map_key = MAP_KEY
    map_layers = mark_safe(simplejson.dumps(MAP_LAYERS))
    (minLon, maxLon, minLat, maxLat) = (mark_safe(MIN_LON),
                                        mark_safe(MAX_LON), mark_safe(MIN_LAT), mark_safe(MAX_LAT))
    start_date, end_date, min_date, max_date = get_dates()
    return render_to_response('cvs/map.html',
                              dict(start_ts=start_date, end_ts=end_date,min_ts=min_date, max_ts=max_date, minLon=minLon, maxLon=maxLon, minLat=minLat
                                   , maxLat=maxLat, map_key=map_key, map_layers=map_layers, base_layer=BASELAYER),
                              context_instance=RequestContext(request))

class JsonResponse(HttpResponse):
    """ return json content type   """

    def __init__(self, obj):
        self.original_obj = obj
        HttpResponse.__init__(self, self.serialize())
        self['Content-Type'] = 'text/javascript'

    def serialize(self):
        return simplejson.dumps(self.original_obj)




def epi_kind(request, kind):
    start_date = datetime.datetime.fromtimestamp(int(request.GET.get('start', get_dates()[0]))//1000)
    end_date = datetime.datetime.fromtimestamp(int(request.GET.get('end', get_dates()[1]))//1000)
    minLat = request.GET.get('minLat', MIN_LAT)
    maxLat = request.GET.get('maxLat', MAX_LAT)
    minLon = request.GET.get('minLon', MIN_LON)
    maxLon = request.GET.get('maxLon', MAX_LON)
    other = [
            'me',
            'ab',
            'af',
            'yf',
            'ch',
            'gw',
            'mg',
            'nt',
            'pl',
            'rb',
    ]
    
    epi_facility_reports=report('epi',attribute_keyword=kind,  group_by = GROUP_BY_FACILITY, start_date=start_date, end_date=end_date,minLat=minLat,maxLat=maxLat,minLon=minLon,maxLon=maxLon)
    if kind == 'other':
        other_epis = {}
        epi_rep=[]
        for epi in other:
            rep=report('epi',attribute_keyword=epi,  group_by = GROUP_BY_FACILITY, start_date=start_date, end_date=end_date,minLat=minLat,maxLat=maxLat,minLon=minLon,maxLon=maxLon)
            other_epis[epi] =rep
            epi_rep=epi_rep+rep

        #sort the list of dictionaries in descending order on value
        epi_facility_reports=sorted(epi_rep, key=lambda k: k['value'],reverse=True)

    epi_reports = []
    for facility in epi_facility_reports:
        epi = {}
        epi['title'] = facility['facility_name']
        epi['lat'] = float(facility['latitude'])
        epi['lon'] = float(facility['longitude'])
        if kind == 'other':
            desc = ""
            for o in other:
                for f in other_epis[o]:
                    if f['facility_id']==facility['facility_id']:
                        desc = desc + " " + o + ":" + str(f['value'])+" cases"
            epi['desc'] = desc

        else:
            epi['desc'] = "<b>" + str(kind) + "</b>:" + str(facility['value']) + "cases";
        epi['heat'] = facility['value'] / float(epi_facility_reports[0]['value'])
        epi['color'] = MAP_LAYERS[kind][2]
        epi_reports.append(epi)
    return JsonResponse(epi_reports)


def health_facilities(request):
    facility_list = []
    health_facilities = HealthFacility.objects.all()
    for facility in health_facilities:
        if facility.location:
            fac = {}
            fac['title'] = facility.name
            fac['lat'] = float(facility.location.latitude)
            fac['lon'] = float(facility.location.longitude)
            fac['icon'] = settings.MEDIA_URL + "cvs/icons/" + facility.type.name.upper() + '.png'
            fac['desc'] = facility.name
            #fac['color'] = MAP_LAYERS['health_facilities'][2]
            facility_list.append(fac)

    return JsonResponse(facility_list)


def malnutrition(request):
    start_date = datetime.datetime.fromtimestamp(int(request.GET.get('start', get_dates()[0]))//1000)
    end_date = datetime.datetime.fromtimestamp(int(request.GET.get('end', get_dates()[1]))//1000)
    minLat = request.GET.get('minLat', MIN_LAT)
    maxLat = request.GET.get('maxLat', MAX_LAT)
    minLon = request.GET.get('minLon', MIN_LON)
    maxLon = request.GET.get('maxLon', MAX_LON)
    malnutrition_reports = []
    muac_facility_reports=report('muac',  group_by = GROUP_BY_FACILITY, start_date=start_date, end_date=end_date,minLat=minLat,maxLat=maxLat,minLon=minLon,maxLon=maxLon)
    for facility in muac_facility_reports:
        muac = {}
        muac['title'] = facility['facility_name']
        muac['lat'] = float(facility['latitude'])
        muac['lon'] = float(facility['longitude'])
        muac['desc'] = "<b>Malnutrition:</b>" +  str(facility['value']) + "cases";
        muac['heat'] = facility['value'] / float(muac_facility_reports[0]['value'])
        muac['color'] = MAP_LAYERS['malnutrition'][2]
        malnutrition_reports.append(muac)
    return JsonResponse(malnutrition_reports)

def births(request):
    start_date = datetime.datetime.fromtimestamp(int(request.GET.get('start', get_dates()[0]))//1000)
    end_date = datetime.datetime.fromtimestamp(int(request.GET.get('end', get_dates()[1]))//1000)
    minLat = request.GET.get('minLat', MIN_LAT)
    maxLat = request.GET.get('maxLat', MAX_LAT)
    minLon = request.GET.get('minLon', MIN_LON)
    maxLon = request.GET.get('maxLon', MAX_LON)
    birth_reports = []
    birth_facility_reports=report('birth',  group_by = GROUP_BY_FACILITY, start_date=start_date, end_date=end_date,minLat=minLat,maxLat=maxLat,minLon=minLon,maxLon=maxLon)
    for facility in birth_facility_reports:
        birth = {}
        birth['title'] = facility['facility_name']
        birth['lat'] = float(facility['latitude'])
        birth['lon'] = float(facility['longitude'])
        birth['desc'] = "<b>Births:</b>" + str(facility['value']) + "cases";
        birth['heat'] = facility['value'] / float(birth_facility_reports[0]['value'])
        birth['color'] = MAP_LAYERS['malnutrition'][2]
        birth_reports.append(birth)
    return JsonResponse(birth_reports)

def deaths(request):
    start_date = datetime.datetime.fromtimestamp(int(request.GET.get('start', get_dates()[0]))//1000)
    end_date = datetime.datetime.fromtimestamp(int(request.GET.get('end', get_dates()[1]))//1000)
    minLat = request.GET.get('minLat', MIN_LAT)
    maxLat = request.GET.get('maxLat', MAX_LAT)
    minLon = request.GET.get('minLon', MIN_LON)
    maxLon = request.GET.get('maxLon', MAX_LON)
    death_reports = []
    death_facility_reports=report('death',  group_by = GROUP_BY_FACILITY, start_date=start_date, end_date=end_date,minLat=minLat,maxLat=maxLat,minLon=minLon,maxLon=maxLon)
    for facility in death_facility_reports:
        death = {}
        death['title'] = facility['facility_name']
        death['lat'] = float(facility['latitude'])
        death['lon'] = float(facility['longitude'])
        death['desc'] = "<b>Deaths:</b>" + str(facility['value']) + "cases";
        death['heat'] = facility['value'] / float(death_facility_reports[0]['value'])
        death['color'] = MAP_LAYERS['malnutrition'][2]
        death_reports.append(death)
    return JsonResponse(death_reports)
