from django.conf.urls.defaults import *
from cvs.views.stats import *
from cvs.views.chart import *
from cvs.views import reporters
from cvs.views import map
from healthmodels import *
from generic.views import generic, generic_row
from generic.sorters import SimpleSorter, QuickSorter
from contact.forms import FreeSearchForm, DistictFilterForm, MassTextForm
from cvs.forms import FacilityFilterForm
from cvs.utils import get_reporters
from cvs.sorters import LatestSubmissionSorter
from healthmodels.models.HealthProvider import HealthProviderBase
from django.contrib.auth.decorators import login_required

urlpatterns = patterns('',
   url(r'^cvs/stats/$', index,name='stats'),
   url(r'^cvs/stats/(?P<location_id>\d+)/$', index),
   url(r'^cvs/muac/$', muac_detail),
   url(r'^cvs/muac/(?P<location_id>\d+)/$', muac_detail),
   url(r'^cvs/epi/$', epi_detail),
   url(r'^cvs/epi/(?P<location_id>\d+)/$', epi_detail),
   url(r'^cvs/birth/$', birth_detail),
   url(r'^cvs/birth/(?P<location_id>\d+)/$', birth_detail),
   url(r'^cvs/death/$', death_detail),
   url(r'^cvs/death/(?P<location_id>\d+)/$', death_detail),
   url(r'^cvs/home/$', home_detail),
   url(r'^cvs/home/(?P<location_id>\d+)/$', home_detail),
   #chart urls
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-zA-Z_]+)/(?P<attribute_value>[0-9a-zA-Z_]+)/(?P<extra_param>[0-9a-zA-Z_]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-zA-Z_]+)/(?P<attribute_value>[0-9a-zA-Z_]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/',chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)', chart),
   #map urls
   url(r'^cvs/map/$', map.map_index, name='map'),
   url(r'^cvs/map/health_facilities', map.health_facilities),
   url(r'^cvs/map/births', map.births),
   url(r'^cvs/map/epi/(?P<kind>[-a-z]+)', map.epi_kind),
   url(r'^cvs/map/malnutrition', map.malnutrition),
   url(r'^cvs/map/deaths', map.deaths),
   #reporters
    url(r'^cvs/reporter/$', login_required(generic), {
      'model':HealthProviderBase,
      'queryset':get_reporters,
      'filter_forms':[FreeSearchForm, DistictFilterForm, FacilityFilterForm],
      'action_forms':[MassTextForm],
      'objects_per_page':25,
      'partial_row':'cvs/partials/reporter_row.html',
      'base_template':'cvs/contacts_base.html',
      'columns':[('Name', True, 'name', SimpleSorter()),
                 ('Number', True, 'connection__identity', SimpleSorter(),),
                 ('Role(s)', True, 'groups__name', SimpleSorter(),),
                 ('District', False, 'district', None,),
                 ('Last Reporting Date', True, 'latest_submission_date', LatestSubmissionSorter(),),
                 ('Total Reports', True, 'connection__submissions__count', SimpleSorter(),),
                 ('Facility',True,'facility__name', SimpleSorter(),),
                 ('Location',True,'location__name', SimpleSorter(),),
                 ('',False,'',None,)],
    }, name="cvs-contact"),
    url(r'^cvs/reporter/(?P<reporter_pk>\d+)/edit', reporters.editReporter),
    url(r'^cvs/reporter/(?P<reporter_pk>\d+)/delete', reporters.deleteReporter),
    url(r'^cvs/reporter/(?P<pk>\d+)/show', generic_row, {'model':HealthProviderBase, 'partial_row':'cvs/partials/reporter_row.html'}),
   )



