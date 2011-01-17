import datetime
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.safestring import mark_safe
from django.utils import simplejson
from django.http import HttpResponse
from django.db import connection
from django.conf import settings
import string


from healthmodels.models.HealthFacility import HealthFacility
from cvs.settings import MAP_KEY, MAP_LAYERS, MIN_LAT,MAX_LAT,MIN_LON,MAX_LON
from cvs.utils import report, reorganize_location, reorganize_timespan, GROUP_BY_LOCATION, GROUP_BY_WEEK, GROUP_BY_MONTH, GROUP_BY_YEAR, GROUP_BY_DAY, GROUP_BY_QUARTER


def get_dates():
    cursor = connection.cursor()
    cursor.execute("select min(created), max(created) from rapidsms_xforms_xformsubmission")
    min_date, end_date = cursor.fetchone()
    start_date = end_date - datetime.timedelta(days=30)
    return (start_date,end_date)
def map_index(request):
    map_key = MAP_KEY
    map_layers = mark_safe(simplejson.dumps(MAP_LAYERS))
    (minLon, maxLon, minLat, maxLat) = (mark_safe(MIN_LON),
                                        mark_safe(MAX_LON), mark_safe(MIN_LAT), mark_safe(MAX_LAT))
    start_date,end_date=get_dates()
    return render_to_response('cvs/map.html',dict(start_date=start_date,end_date=end_date,minLon=minLon, maxLon=maxLon, minLat=minLat, maxLat=maxLat,map_key=map_key,map_layers=map_layers) ,context_instance=RequestContext(request))

class JsonResponse(HttpResponse):

    """ return json content type   """

    def __init__(self, obj):
        self.original_obj = obj
        HttpResponse.__init__(self, self.serialize())
        self['Content-Type'] = 'text/javascript'

    def serialize(self):
        return simplejson.dumps(self.original_obj)


def reports_per_healthfacilities(xform_keyword,start_date,end_date,minLat,maxLat,minLon,maxLon):
    cursor=connection.cursor()
    keyword=xform_keyword
    if keyword.startswith("'epi") :
        REPORTS_QUERY="""
                        SELECT  SUM(value_int)         AS value,
                                providers.facility_id AS facility_id,
                                    facility.name         AS facility_name,
                                    TYPE.name             AS type_name,
                                    location.latitude     AS latitude,
                                    location.longitude    AS longitude
                            FROM   eav_value AS values
                                   JOIN eav_attribute attributes
                                     ON values.attribute_id = attributes.id
                                   JOIN rapidsms_xforms_xformsubmission submissions
                                     ON values.entity_id = submissions.id
                                   JOIN rapidsms_connection connections
                                     ON submissions.connection_id = connections.id
                                   JOIN healthmodels_healthproviderbase providers
                                     ON connections.contact_id = providers.contact_ptr_id
                                   JOIN healthmodels_healthfacilitybase facility
                                     ON providers.facility_id = facility.id
                                   JOIN healthmodels_healthfacilitytypebase TYPE
                                     ON TYPE.id = facility.type_id
                                   JOIN simple_locations_point location
                                     ON facility.location_id = location.id
                            WHERE
                                        attributes.slug in (%(xform_keyword)s)
                                   AND submissions.created >= date '%(start_date)s'
                                   AND submissions.created <= date '%(end_date)s'
                                   AND location.latitude >= %(minLat)s
                                   AND location.latitude <= %(maxLat)s
                                   AND location.longitude >= %(minLon)s
                                   AND location.longitude <= %(maxLon)s
                            GROUP  BY facility_id,
                                      facility_name,
                                      type_name,
                                      latitude,
                                      longitude
                            ORDER  BY value DESC;
                     """
    else:


        REPORTS_QUERY = """SELECT COUNT(submissions.id) AS VALUE,
                           providers.facility_id AS facility_id,
                           facility.name         AS facility_name,
                           TYPE.name             AS type_name,
                           location.latitude     AS latitude,
                           location.longitude    AS longitude
                    FROM   rapidsms_xforms_xformsubmission AS submissions
                           JOIN rapidsms_xforms_xform xforms
                             ON submissions.xform_id = xforms.id
                           JOIN rapidsms_connection connections
                             ON submissions.connection_id = connections.id
                           JOIN healthmodels_healthproviderbase providers
                             ON connections.contact_id = providers.contact_ptr_id
                           JOIN healthmodels_healthfacilitybase facility
                             ON providers.facility_id = facility.id
                           JOIN healthmodels_healthfacilitytypebase TYPE
                             ON TYPE.id = facility.type_id
                           JOIN simple_locations_point location
                             ON facility.location_id = location.id
                    WHERE  xforms.keyword = '%(xform_keyword)s'
                           AND submissions.created >= date '%(start_date)s'
                           AND submissions.created <= date '%(end_date)s'
                           AND location.latitude >= %(minLat)s
                           AND location.latitude <= %(maxLat)s
                           AND location.longitude >= %(minLon)s
                           AND location.longitude <= %(maxLon)s

                    GROUP  BY facility_id,
                              facility_name,
                              type_name,
                              latitude,
                              longitude
                    ORDER  BY value DESC;"""
    start_date=datetime.datetime.strftime(start_date, '%Y-%m-%d')
    end_date=datetime.datetime.strftime(end_date, '%Y-%m-%d')
    sql=REPORTS_QUERY%{
                        'xform_keyword':xform_keyword,
                        'start_date':start_date,
                        'end_date':end_date,
                        'minLat':minLat,
                        'maxLat':maxLat,
                        'minLon':minLon,
                        'maxLon':maxLon,



                        }
    print sql
    cursor.execute(sql)
    rows = cursor.fetchall()
    facility_reports=[]

    for row in rows:
        rep={}
        rep['value']=row[0]
        rep['facility_id']=row[1]
        rep['facility_name']=row[2]
        rep['type']=row[3]
        rep['latitude']=float(row[4])
        rep['longitude']=float(row[5])
        facility_reports.append(rep)
    return facility_reports







def epi_kind(request, kind):
    start_date = request.GET.get('start', get_dates()[0])
    end_date = request.GET.get('end', get_dates()[1])
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

    if kind=='other':
        xform_keyword=','.join(["'epi_"+epi+"'" for epi in other])
    else:
        xform_keyword="'epi_"+str(kind)+"'"

    epi_facility_reports=reports_per_healthfacilities(xform_keyword,start_date,end_date,minLat,maxLat,minLon,maxLon)
    epi_reports=[]
    for facility in epi_facility_reports:
        epi={}
        epi['title']=facility['facility_name']
        epi['lat']=facility['latitude']
        epi['lon']=facility['longitude']
        epi['desc']=facility['type']
        epi['heat']=facility['value']/float(epi_facility_reports[0]['value'])
        epi['color']=MAP_LAYERS[kind][2]
        epi_reports.append(epi)
    return JsonResponse(epi_reports)


def health_facilities(request):
    facility_list = []
    health_facilities=HealthFacility.objects.all()
    for facility in health_facilities:
        if facility.location:
            fac={}
            fac['title']=facility.name
            fac['lat']=float(facility.location.latitude)
            fac['lon']=float(facility.location.longitude) 
            fac['icon']=settings.MEDIA_URL+"cvs/icons/" + facility.type.name.upper() + '.png'
            fac['desc']=facility.name
            fac['color'] = MAP_LAYERS['health_facilities'][2]
            facility_list.append(fac)

        
    return JsonResponse(facility_list)


def malnutrition(request):
    start_date = request.GET.get('start', get_dates()[0])
    end_date = request.GET.get('end', get_dates()[1])
    minLat = request.GET.get('minLat', MIN_LAT)
    maxLat = request.GET.get('maxLat', MAX_LAT)
    minLon = request.GET.get('minLon', MIN_LON)
    maxLon = request.GET.get('maxLon', MAX_LON)
    malnutrition_reports=[]
    muac_facility_reports=reports_per_healthfacilities('muac',start_date,end_date,minLat,maxLat,minLon,maxLon)
    for facility in muac_facility_reports:
        muac={}
        muac['title']=facility['facility_name']
        muac['lat']=facility['latitude']
        muac['lon']=facility['longitude']
        muac['desc']=facility['type']
        muac['heat']=facility['value']/float(muac_facility_reports[0]['value'])
        muac['color']=MAP_LAYERS['malnutrition'][2]
        malnutrition_reports.append(muac)
    return JsonResponse(malnutrition_reports)

def births(request):
    start_date = request.GET.get('start', get_dates()[0])
    end_date = request.GET.get('end', get_dates()[1])
    minLat = request.GET.get('minLat', MIN_LAT)
    maxLat = request.GET.get('maxLat', MAX_LAT)
    minLon = request.GET.get('minLon', MIN_LON)
    maxLon = request.GET.get('maxLon', MAX_LON)
    birth_reports=[]
    birth_facility_reports=reports_per_healthfacilities('birth',start_date,end_date,minLat,maxLat,minLon,maxLon)
    for facility in birth_facility_reports:
        birth={}
        birth['title']=facility['facility_name']
        birth['lat']=facility['latitude']
        birth['lon']=facility['longitude']
        birth['desc']=facility['type']
        birth['heat']=facility['value']/float(birth_facility_reports[0]['value'])
        birth['color']=MAP_LAYERS['malnutrition'][2]
        birth_reports.append(birth)
    return JsonResponse(birth_reports)

def deaths(request):
    start_date = request.GET.get('start', get_dates()[0])
    end_date = request.GET.get('end', get_dates()[1])
    minLat = request.GET.get('minLat', MIN_LAT)
    maxLat = request.GET.get('maxLat', MAX_LAT)
    minLon = request.GET.get('minLon', MIN_LON)
    maxLon = request.GET.get('maxLon', MAX_LON)
    death_reports = []
    death_facility_reports=reports_per_healthfacilities('death',start_date,end_date,minLat,maxLat,minLon,maxLon)
    for facility in death_facility_reports:
        death={}
        death['title']=facility['facility_name']
        death['lat']=facility['latitude']
        death['lon']=facility['longitude']
        death['desc']=facility['type']
        death['heat']=facility['value']/float(death_facility_reports[0]['value'])
        death['color']=MAP_LAYERS['malnutrition'][2]
        death_reports.append(death)
    return JsonResponse(death_reports)
