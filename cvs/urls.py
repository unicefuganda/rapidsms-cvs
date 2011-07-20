from django.conf.urls.defaults import *
from cvs.views.stats import *
from cvs.views.chart import *
from cvs.views import basic, reporters, map
from healthmodels import *
from generic.views import generic, generic_row, generic_dashboard, generic_map
from generic.sorters import SimpleSorter, TupleSorter
from contact.forms import FreeSearchForm, DistictFilterForm, MassTextForm
from cvs.forms import FacilityFilterForm, ChartModuleForm, StatsModuleForm,MapModuleForm
from cvs.utils import get_reporters
from cvs.sorters import LatestSubmissionSorter
from cvs.views.dates import get_dates
from healthmodels.models.HealthProvider import HealthProviderBase
from django.contrib.auth.decorators import login_required
from rapidsms_xforms.models import XForm
from .utils import get_messages, get_mass_messages
from rapidsms_httprouter.models import Message
from ureport.models import MassText
from contact.forms import FreeSearchTextForm, DistictFilterMessageForm, HandledByForm, ReplyTextForm

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
   url(r'^cvs/data/excelexport/$', export_as_excel),
   #chart urls
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-zA-Z_]+)/(?P<attribute_value>[0-9a-zA-Z_]+)/(?P<extra_param>[0-9a-zA-Z_]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-zA-Z_]+)/(?P<attribute_value>[0-9a-zA-Z_]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/',chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)', chart),
    url(r'^cvs/chart/(?P<location_id>\d+)/active_reporters/$', active_reporters_chart),
   #map urls
   url(r'^cvs/map/(?P<layer>[a-z_]+)/(?P<kind>[-a-z]+)', map.map_index,name='map'),
   url(r'^cvs/map/(?P<layer>[a-z_]+)',map.map_index),
   url(r'^cvs/map/$',map.map_index),
#   url(r'^cvs/map/health_facilities', map.health_facilities),
#   url(r'^cvs/map/births', map.births),
#   url(r'^cvs/map/epi/(?P<kind>[-a-z]+)', map.epi_kind),
#   url(r'^cvs/map/malnutrition', map.malnutrition),
#   url(r'^cvs/map/deaths', map.deaths),
   #reporters
    url(r'^cvs/reporter/$', login_required(generic), {
      'model':HealthProviderBase,
      'queryset':get_reporters,
      'filter_forms':[FreeSearchForm, DistictFilterForm, FacilityFilterForm],
      'action_forms':[MassTextForm],
      'objects_per_page':25,
      'partial_row':'cvs/partials/reporter_row.html',
      'base_template':'cvs/contacts_base.html',
      'results_title':'Reporters',
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
    url(r'^cvs/forms/$', login_required(generic),  {
        'model':XForm,
#        'queryset':get_contacts,
#        'filter_forms':[FreeSearchForm, DistictFilterForm, FilterGroupsForm],
#        'action_forms':[MassTextForm, AssignGroupForm, BlacklistForm],
        'objects_per_page':10,
        'selectable':False,
        'partial_row':'cvs/partials/form_row.html',
        'base_template':'cvs/xform_admin_base.html',
        'results_title':'Forms',
        'columns':[('Name', True, 'name', SimpleSorter()),
                 ('Description', True, 'description', SimpleSorter(),),
                 ('',False,'',None)],
    }, name="cvs-forms"),
    url(r'^cvs/module_stats/(?P<location_id>\d+)/(?P<view_name>[a-z_]+)/$', module_stats),
    url(r"^cvs/forms/(\d+)/submissions/$", login_required(basic.view_submissions)),
    url(r'^cvs/dashboard/$', generic_dashboard,{
           'slug':'cvs',
        'module_types':[('chart', ChartModuleForm, 'CVS Chart Module',),('map',MapModuleForm,'Cvs Map Module',),('module_stats', StatsModuleForm, 'CVS Statistics Module',),],
        'base_template':'generic/dashboard_base.html',
   }),
   url(r'^cvs/messagelog/$', login_required(generic), {
      'model':Message,
      'queryset':get_messages,
      'filter_forms':[FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
      'action_forms':[ReplyTextForm],
      'objects_per_page':25,
      'partial_row':'contact/partials/message_row.html',
      'base_template':'cvs/messages_base.html',
      'columns':[('Text', True, 'text', SimpleSorter()),
                 ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
                 ('Date', True, 'date', SimpleSorter(),),
                 ('Type', True, 'application', SimpleSorter(),),
                 ('Response', False, 'response', None,),
                 ],
      'sort_column':'date',
      'sort_ascending':False,
    }, name="cvs-messagelog"),
   url(r'^cvs/massmessages/$', login_required(generic), {
      'model':MassText,
      'queryset':get_mass_messages,
      'objects_per_page':10,
      'partial_row':'contact/partials/mass_message_row.html',
      'base_template':'cvs/mass_messages_base.html',
      'columns':[('Message', True, 'text', TupleSorter(0)),
                 ('Time', True, 'date', TupleSorter(1),),
                 ('User', True, 'user', TupleSorter(2),),
                 ('Recipients', True, 'response', TupleSorter(3),),
                 ('Type', True, 'type', TupleSorter(4),),
                 ],
      'sort_column':'date',
      'sort_ascending':False,
      'selectable':False,
    }),
    url(r'^cvs/stats/(?P<start_date>\d+)/(?P<end_date>\d+)/(?P<xform_keyword>[a-z]+)/((?P<attribute_keyword>[a-zA-Z_]+)/)?', map.map_api),
    url(r'^cvs/stats/healthfacility', map.health_facility_api),
    url(r'^cvs/maptest/', generic_map, { 
        'map_layers' : [{'name':'HCs','url':'/cvs/stats/healthfacility','autoload':True},
                        {'name':'MUAC','url':'/cvs/stats/1278450000/1310504400/muac/','color':'#3D96AE','needs_date':True},
                       ],
        'dates': get_dates,\
    }),
)



