from django.conf.urls.defaults import *
from cvs.views.stats import *
from cvs.views.chart import chart, chart_api, active_reporters_chart
from cvs.views import basic, reporters, map
from healthmodels import *
from generic.views import generic, generic_row, generic_dashboard, generic_map
from generic.sorters import SimpleSorter, TupleSorter
from contact.forms import FreeSearchForm, DistictFilterForm, MassTextForm
from cvs.forms import ActivateForm, FacilityFilterForm, ChartModuleForm, StatsModuleForm, MapModuleForm
from cvs.utils import get_reporters
from cvs.sorters import LatestSubmissionSorter, LatestJoinedSorter
from cvs.views.dates import get_dates
from cvs.views.basic import ussd_test
from healthmodels.models.HealthProvider import HealthProviderBase
from django.contrib.auth.decorators import login_required
from rapidsms_xforms.models import XForm
from .utils import get_messages, get_mass_messages, get_training_messages, get_training_vhts, get_dashboard_messages
from rapidsms_httprouter.models import Message
from contact.models import MassText
from contact.forms import FreeSearchTextForm, DistictFilterMessageForm, HandledByForm, ReplyTextForm
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
   url(r'^cvs/stats/$', index, name='stats'),
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
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)', chart),
   url(r'^cvs/chart/(?P<location_id>\d+)/active_reporters/$', active_reporters_chart),
   url(r'^cvs/api/charts/(?P<start_date>\d+)/(?P<end_date>\d+)/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/((?P<attribute_keyword>[a-zA-Z_]+)/)?', chart_api),

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
                 ('Facility', True, 'facility__name', SimpleSorter(),),
                 ('Location', True, 'location__name', SimpleSorter(),),
                 ('', False, '', None,)],
    }, name="cvs-contact"),
    url(r'^cvs/reporter/(?P<reporter_pk>\d+)/edit', reporters.editReporter),
    url(r'^cvs/reporter/(?P<reporter_pk>\d+)/locations/edit/((?P<district_pk>\d+)/)?', reporters.editReporterLocations),
    url(r'^cvs/reporter/(?P<reporter_pk>\d+)/facilities/edit/((?P<district_pk>\d+)/)?', reporters.editReporterFacilities),
    url(r'^cvs/reporter/(?P<reporter_pk>\d+)/delete', reporters.deleteReporter),

    url(r'^cvs/reporter/(?P<pk>\d+)/show', generic_row, {'model':HealthProviderBase, 'partial_row':'cvs/partials/reporter_row.html'}),
    url(r'^cvs/forms/$', login_required(generic), {
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
                 ('', False, '', None)],
    }, name="cvs-forms"),
    url(r'^cvs/module_stats/(?P<location_id>\d+)/(?P<view_name>[a-z_]+)/$', module_stats),
    url(r"^cvs/forms/(\d+)/submissions/$", login_required(basic.view_submissions)),
    url(r'^cvs/dashboard/$', generic_dashboard, {
           'slug':'cvs',
        'module_types':[('chart', ChartModuleForm, 'CVS Chart Module',), ('map', MapModuleForm, 'Cvs Map Module',), ('module_stats', StatsModuleForm, 'CVS Statistics Module',), ],
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

    # map API calls
    url(r'^cvs/stats/(?P<start_date>\d+)/(?P<end_date>\d+)/(?P<xform_keyword>[a-z]+)/((?P<attribute_keyword>[a-zA-Z_]+)/)?', map.map_api),
    url(r'^cvs/stats/(?P<start_date>\d+)/(?P<end_date>\d+)/2/epi/other/', map.map_other_api),
    url(r'^cvs/stats/healthfacility', map.health_facility_api),

    # map view
    url(r'^cvs/map/', generic_map, {
        'map_layers' : [{'name':'Health Facilities', 'url':'/cvs/stats/healthfacility', 'autoload':True},
                        {'name':'Malnutrition', 'url':'/cvs/stats/<start_ts>/<end_ts>/muac/', 'color':'#80699B', 'needs_date':True},
                        {'name':'Deaths', 'url':'/cvs/stats/<start_ts>/<end_ts>/death/', 'color':'#AA4643', 'needs_date':True},
                        {'name':'Births', 'url':'/cvs/stats/<start_ts>/<end_ts>/birth/', 'color':'#89A54E', 'needs_date':True},
                        {'name':'Malaria', 'url':'/cvs/stats/<start_ts>/<end_ts>/epi/ma/', 'color':'#3D96AE', 'needs_date':True},
                        {'name':'Dysentery', 'url':'/cvs/stats/<start_ts>/<end_ts>/epi/bd/', 'color':'#DB843D', 'needs_date':True},
                        {'name':'Tuberculosis', 'url':'/cvs/stats/<start_ts>/<end_ts>/epi/tb/', 'color':'#92A8CD', 'needs_date':True},
                        {'name':'Other Diseases', 'url':'/cvs/stats/<start_ts>/<end_ts>/2/epi/other/', 'color':'#A47D7C', 'needs_date':True},
                       ],
        'dates': get_dates, \
        'display_autoload': False, \
    }, name="cvs-map"),

   #reporters
    url(r'^cvs/train/reporter/$', login_required(generic), {
      'model':HealthProviderBase,
      'queryset':get_training_vhts,
      'filter_forms':[FreeSearchForm, DistictFilterForm, FacilityFilterForm],
      'action_forms':[MassTextForm, ActivateForm],
      'objects_per_page':25,
      'partial_row':'cvs/partials/trainee_row.html',
      'base_template':'cvs/contacts_base.html',
      'results_title':'Reporters',
      'sort_column':'join_date',
      'sort_ascending':False,
      'columns':[('Name', True, 'name', SimpleSorter()),
                 ('Number', True, 'connection__identity', SimpleSorter(),),
                 ('Role(s)', True, 'groups__name', SimpleSorter(),),
                 ('District', False, 'district', None,),
                 ('Join Date', True, 'join_date', LatestJoinedSorter(),),
                 ('Total Reports', True, 'connection__submissions__count', SimpleSorter(),),
                 ('Facility', True, 'facility__name', SimpleSorter(),),
                 ('Location', True, 'location__name', SimpleSorter(),),
                 ('', False, '', None,)],
    }, name="cvs-training-contact"),
   url(r'^cvs/train/messagelog/$', login_required(generic), {
      'model':Message,
      'queryset':get_training_messages,
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
    }, name="cvs-training-messagelog"),

)



