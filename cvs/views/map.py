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

class JsonResponse(HttpResponse):
    """ return json content type   """

    def __init__(self, obj):
        self.original_obj = obj
        HttpResponse.__init__(self, self.serialize())
        self['Content-Type'] = 'text/javascript'

    def serialize(self):
        return simplejson.dumps(self.original_obj)

def map_index(request,layer=None,kind=None,template="cvs/map.html"):

    map_key = MAP_KEY
    map_layers = mark_safe(simplejson.dumps(MAP_LAYERS))
    health_facilities = HealthFacility.objects.all()
    data_list=[]
    minLat = request.GET.get('minLat', MIN_LAT)
    maxLat = request.GET.get('maxLat', MAX_LAT)
    minLon = request.GET.get('minLon', MIN_LON)
    maxLon = request.GET.get('maxLon', MAX_LON)
    min_date, max_date = get_dates()[2],get_dates()[3]

    start_date = datetime.datetime.fromtimestamp(int(request.GET.get('start', get_dates()[0]))//1000)
    end_date = datetime.datetime.fromtimestamp(int(request.GET.get('end', get_dates()[1]))//1000)


    (minLon, maxLon, minLat, maxLat) = (mark_safe(MIN_LON),
                                        mark_safe(MAX_LON), mark_safe(MIN_LAT), mark_safe(MAX_LAT))

    if request.GET.get('module',None):
            template="cvs/partials/map_module.html"
    facility_icons={}
    for facility in health_facilities:
            if facility.location:
                facility_icons[str(facility.name.lower())] = str(settings.MEDIA_URL + "cvs/icons/" + facility.type.name.upper() + '.png')
    print facility_icons 
    if layer == 'health_facilities' :
        for facility in health_facilities:
            if facility.location:
                fac = {}
                fac['title'] = str(facility.name)
                fac['lat'] = float(facility.location.latitude)
                fac['lon'] = float(facility.location.longitude)
                fac['icon'] = settings.MEDIA_URL + "cvs/icons/" + facility.type.name.upper() + '.png'
                fac['desc'] = facility.name
                #fac['color'] = MAP_LAYERS['health_facilities'][2]
                data_list.append(fac)
    elif layer == 'epi':
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
            epi['title'] = str(facility['facility_name'])
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
                epi['desc'] = "<b>" + str(kind) + "</b>:" + str(facility['value']) + " cases"
            epi['heat'] = facility['value'] / float(epi_facility_reports[0]['value'])
            epi['color'] = MAP_LAYERS[kind][2]
            epi['icon'] = facility_icons[str(facility['facility_name']).lower()]
            data_list.append(epi)

    elif layer:
        layers={'malnutrition':(('muac'),('Malnutrition'),),'births':(('birth'),('Births'),),'deaths':(('death'),('Deaths'),)}
        reports=report(layers[layer][0],  group_by = GROUP_BY_FACILITY, start_date=start_date, end_date=end_date,minLat=minLat,maxLat=maxLat,minLon=minLon,maxLon=maxLon)
        for facility in reports:
            rep = {}
            rep['title'] = str(facility['facility_name'])
            rep['lat'] = float(facility['latitude'])
            rep['lon'] = float(facility['longitude'])
            rep['desc'] = "<b>layers[layer][1]:</b>" +  str(facility['value']) + " cases"
            rep['heat'] = facility['value'] / float(reports[0]['value'])
            rep['color'] = MAP_LAYERS[layer][2]
            rep['icon'] = facility_icons[str(facility['facility_name'])]
            data_list.append(rep)
    else:

        return render_to_response(template,
                                  dict(start_ts=get_dates()[0], end_ts=get_dates()[1],min_ts=min_date, max_ts=max_date, minLon=minLon, maxLon=maxLon, minLat=minLat
                                       , maxLat=maxLat, map_key=map_key, map_layers=map_layers, base_layer=BASELAYER),
                                  context_instance=RequestContext(request))
    if request.GET.get('module',None):
        template="cvs/partials/map_module.html"
        return render_to_response(template,
                                  dict(start_ts=get_dates()[0], end_ts=get_dates()[1],min_ts=min_date, max_ts=max_date, minLon=minLon, maxLon=maxLon, minLat=minLat
                                       , maxLat=maxLat, map_key=map_key,data=mark_safe(data_list), map_layers=map_layers, base_layer=BASELAYER),
                                  context_instance=RequestContext(request))
    return JsonResponse(data_list)



