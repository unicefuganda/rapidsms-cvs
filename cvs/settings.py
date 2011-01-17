from django.utils.datastructures import SortedDict



## set the overlay colors and icons
MAP_LAYERS = SortedDict([
    ('health_facilities', ['Health Facilities', '/cvs/map/health_facilities','#4572A7']),
    ('deaths', ['Deaths','/cvs/map/deaths', '#AA4643']),
    ('births', ['Births','/cvs/map/births', '#89A54E']),
    ('malnutrition', ['Malnutrition','/malnutrition', '#80699B']),
    ('ma', ['Malaria','/cvs/map/epi/ma/', '#3D96AE']),
    ('bd', ['Bloody  Diarrhoea','/cvs/map/epi/bd/', '#DB843D']),
    ('tb', ['TuberClosis','/cvs/map/epi/tb/', '#92A8CD']),
    ('other', ['Other','/cvs/map/epi/other/', '#A47D7C'])
    ])

#map bounding box
MIN_LAT = '31.19800'
MAX_LAT = '33.80176'
MIN_LON = '2.1444'
MAX_LON = '3.88875'

##google maps api key
MAP_KEY = \
    'ABQIAAAAYimH_excdTjwGjM6LcP-DhTX43PO8-sEH-jeG6rM560fvsomnhQ4fvBin-y4dRWztAXXs1ap0AwfdQ'

BASELAYER="/cvs/map/health_facilities"