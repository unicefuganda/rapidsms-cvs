import datetime
import time
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.safestring import mark_safe
from django.utils import simplejson
from django.http import HttpResponse
from django.db import connection
from django.conf import settings
from cvs.views.dates import get_dates
from cvs.forms import DateRangeForm

from healthmodels.models.HealthFacility import HealthFacility
from cvs.settings import MAP_KEY, MAP_LAYERS, MIN_LAT, MAX_LAT, MIN_LON, MAX_LON, BASELAYER

from cvs.utils import total_submissions_by_facility, total_attribute_by_facility

#def get_dates():
#    cursor = connection.cursor()
#    cursor.execute("select min(created), max(created) from rapidsms_xforms_xformsubmission")
#    min_date, end_date = cursor.fetchone()
#    start_date = end_date - datetime.timedelta(days=300)
#    start_date=time.mktime(start_date.timetuple()) * 1000
#    end_date=time.mktime(end_date.timetuple()) * 1000
#    max_date =  time.mktime(datetime.datetime.now().timetuple()) * 1000
#    min_date=time.mktime(min_date.timetuple()) * 1000
#
#    return (start_date, end_date, min_date, max_date)

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
    max_date = datetime.datetime.now()
    dates=get_dates(request)
    date_range_form=dates['form']
    max_ts=time.mktime(max_date.timetuple()) * 1000
    min_ts=time.mktime(dates['min'].timetuple()) * 1000
    start_ts=time.mktime(dates['start'].timetuple()) * 1000
    end_ts=time.mktime(dates['end'].timetuple()) * 1000
    start_date = datetime.datetime.fromtimestamp(int(request.GET.get('start', start_ts))//1000)
    end_date = datetime.datetime.fromtimestamp(int(request.GET.get('end', end_ts))//1000)


    (minLon, maxLon, minLat, maxLat) = (mark_safe(MIN_LON),
                                        mark_safe(MAX_LON), mark_safe(MIN_LAT), mark_safe(MAX_LAT))

    if request.GET.get('module',None):
            template="cvs/partials/map_module.html"
    facility_icons={}
    for facility in health_facilities:
            if facility.location:
                facility_icons[str(facility.name.lower())] = str(settings.MEDIA_URL + "cvs/icons/" + facility.type.name.upper() + '.png')
    if layer == 'health_facilities' :
        for facility in health_facilities:
            if facility.location:
                fac = {}
                fac['title'] = str(facility.name)
                fac['lat'] = float(facility.location.latitude)
                fac['lon'] = float(facility.location.longitude)
                fac['icon'] = str(settings.MEDIA_URL + "cvs/icons/" + facility.type.name.upper() + '.png')
                fac['desc'] = str(facility.name)
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
        epi_rep=total_attribute_by_facility('epi_%s'%kind, start_date, end_date, (minLat,minLon,maxLat,maxLon,))
        if kind == 'other':
            other_epis = {}
            epi_rep=[]
            for epi in other:
                rep=total_attribute_by_facility('epi_%s'%epi, start_date, end_date, (minLat,minLon,maxLat,maxLon,))
                other_epis[epi] =rep
                epi_rep=epi_rep+list(rep)

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
        reports=total_submissions_by_facility(layers[layer][0], start_date, end_date, (minLat,minLon,maxLat,maxLon,))
        reports=sorted(reports, key=lambda k: k['value'],reverse=True)
        for facility in reports:
            rep = {}
            rep['title'] = str(facility['facility_name'])
            rep['lat'] = float(facility['latitude'])
            rep['lon'] = float(facility['longitude'])
            rep['desc'] = "<b>"+str(layers[layer][1])+":</b>" +  str(facility['value']) + " cases"
            rep['heat'] = facility['value'] / float(reports[0]['value'])
            rep['color'] = MAP_LAYERS[layer][2]
            rep['icon'] = facility_icons[str(facility['facility_name']).lower()]
            data_list.append(rep)
    else:

        return render_to_response(template,
                                  dict(start_ts=start_ts, end_ts=end_ts,min_ts=min_ts, max_ts=max_ts, minLon=minLon, maxLon=maxLon, minLat=minLat
                                       , maxLat=maxLat, map_key=map_key, map_layers=map_layers,date_range_form=date_range_form, base_layer=BASELAYER),
                                  context_instance=RequestContext(request))
    if request.GET.get('module',None):
        template="cvs/partials/map_module.html"
        return render_to_response(template,
                                  dict(start_ts=start_ts, end_ts=end_ts,min_ts=min_ts, max_ts=max_ts, minLon=minLon, maxLon=maxLon, minLat=minLat
                                       , maxLat=maxLat, map_key=map_key,data=mark_safe(data_list), map_layers=map_layers,date_range_form=date_range_form, base_layer=BASELAYER),
                                  context_instance=RequestContext(request))
    return JsonResponse(data_list)

def map_api(request, start_date, end_date, xform_keyword, attribute_keyword=None):
    start_date=datetime.datetime.fromtimestamp(int(start_date))
    end_date=datetime.datetime.fromtimestamp(int(end_date))
    if attribute_keyword:
        data_function = total_attribute_by_facility
        keyword = "%s_%s" % (xform_keyword, attribute_keyword)
    else:
        data_function = total_submissions_by_facility
        keyword = xform_keyword
#    import pdb;pdb.set_trace()
    data = data_function(keyword, start_date, end_date, (MIN_LAT, MIN_LON, MAX_LAT, MAX_LON))
    for d in data:
        d['lat'] = float(d.pop('latitude'))
        d['lon'] = float(d.pop('longitude'))
        d['location_id'] = d.pop('facility_id')
        d['location_name'] = "%s %s" % (d.pop('facility_name'), d.pop('type').upper())

    json_response_data = {'layer_type':'flat', 'data':list(data)}
    return JsonResponse(json_response_data)

