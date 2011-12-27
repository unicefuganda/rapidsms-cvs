from django.conf.urls.defaults import *
from cvs.views import basic, reporters, map, facilities
from healthmodels import *
from generic.views import generic, generic_row, generic_dashboard, generic_map
from generic.sorters import SimpleSorter, TupleSorter
from contact.forms import FreeSearchForm, DistictFilterForm, MassTextForm
from cvs.forms import ActivateForm, FacilityFilterForm
from cvs.utils import get_reporters
from cvs.sorters import \
    LatestSubmissionSorter, \
    LatestJoinedSorter, \
    LatestFacilitySubmissionSorter, \
    TotalFacilitySubmissionSorter
from uganda_common.reports import XFormDateGetter
from cvs.views.stats import export_as_excel
from healthmodels.models.HealthProvider import HealthProviderBase
from healthmodels.models.HealthFacility import HealthFacilityBase
from django.contrib.auth.decorators import login_required
from rapidsms_xforms.models import XForm
from cvs.utils import get_all_messages, get_unsolicited_messages, get_mass_messages, get_training_messages, get_nolocation_vhts, get_training_vhts, get_dashboard_messages
from mtrack.utils import get_facilites_for_view
from cvs.reports import *
from rapidsms_httprouter.models import Message
from contact.models import MassText
from contact.forms import FreeSearchTextForm, DistictFilterMessageForm, HandledByForm, ReplyTextForm
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
   #############################################
   #              REPORTERS VIEWS              #
   #############################################
   # Registered Users
    url(r'^cvs/reporter/$', login_required(generic), {
      'model':HealthProviderBase,
      'queryset':get_reporters,
      'filter_forms':[FreeSearchForm, DistictFilterForm, FacilityFilterForm],
      'action_forms':[MassTextForm],
      'objects_per_page':25,
      'partial_row':'cvs/reporter/partials/reporter_row.html',
      'partial_header':'cvs/reporter/partials/partial_header.html',
      'base_template':'cvs/reporter/registered_contacts.html',
      'results_title':'Registered Users',
      'columns':[('Name', True, 'name', SimpleSorter()),
                 ('Number', True, 'connection__identity', SimpleSorter(),),
                 ('Role(s)', True, 'groups__name', SimpleSorter(),),
                 ('District', False, 'district', None,),
                 ('Last Reporting Date', True, 'latest_submission_date', LatestSubmissionSorter(),),
                 ('Total Reports', True, 'connection__submissions__count', SimpleSorter(),),
                 ('Facility', True, 'facility__name', SimpleSorter(),),
                 ('Location', True, 'location__name', SimpleSorter(),),
                 ('', False, '', None,)],
      'sort_column':'latest_submission_date',
      'sort_ascending':False,
    }, name="cvs-contact"),
    # Trainees
    url(r'^cvs/train/reporter/$', login_required(generic), {
      'model':HealthProviderBase,
      'queryset':get_training_vhts,
      'filter_forms':[FreeSearchForm, DistictFilterForm, FacilityFilterForm],
      'action_forms':[MassTextForm, ActivateForm],
      'objects_per_page':25,
      'partial_row':'cvs/reporter/partials/trainee_row.html',
      'base_template':'cvs/reporter/training_contacts.html',
      'results_title':'Trainees',
      'sort_column':'join_date',
      'sort_ascending':True,
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
    # Orphaned
    url(r'^cvs/orphaned/reporter/$', login_required(generic), {
      'model':HealthProviderBase,
      'queryset':get_nolocation_vhts,
      'filter_forms':[FreeSearchForm, FacilityFilterForm],
      'action_forms':[MassTextForm, ActivateForm],
      'objects_per_page':25,
      'partial_row':'cvs/reporter/partials/reporter_row.html',
      'base_template':'cvs/reporter/nolocation_contacts.html',
      'results_title':'No Location',
      'sort_column':'join_date',
      'sort_ascending':False,
      'columns':[('Name', True, 'name', SimpleSorter()),
                 ('Number', True, 'connection__identity', SimpleSorter(),),
                 ('Role(s)', True, 'groups__name', SimpleSorter(),),
                 ('District', False, 'district', None,),
                 ('Last Reporting Date', True, 'latest_submission_date', LatestSubmissionSorter(),),
                 ('Total Reports', True, 'connection__submissions__count', SimpleSorter(),),
                 ('Facility', True, 'facility__name', SimpleSorter(),),
                 ('Location', True, 'location__name', SimpleSorter(),),
                 ('', False, '', None,)],
    }, name="cvs-orphan-contact"),

    url(r'^cvs/((train|orphaned)/)?reporter/(?P<reporter_pk>\d+)/edit', reporters.editReporter),
    url(r'^cvs/((train|orphaned)/)?reporter/(?P<reporter_pk>\d+)/locations/edit/((?P<district_pk>\d+)/)?', reporters.editReporterLocations),
    url(r'^cvs/((train|orphaned)/)?reporter/locations/edit/((?P<district_pk>\d+)/)?', reporters.editReporterLocations),
    url(r'^cvs/((train|orphaned)/)?reporter/(?P<reporter_pk>\d+)/facilities/edit/((?P<district_pk>\d+)/)?', reporters.editReporterFacilities),
    url(r'^cvs/((train|orphaned)/)?reporter/facilities/edit/((?P<district_pk>\d+)/)?', reporters.editReporterFacilities),
    url(r'^cvs/((train|orphaned)/)?reporter/(?P<reporter_pk>\d+)/delete', reporters.deleteReporter),
    url(r'^cvs/(orphaned/)?reporter/(?P<pk>\d+)/show', generic_row, {'model':HealthProviderBase, 'partial_row':'cvs/reporter/partials/reporter_row.html'}),
    url(r'^cvs/train/reporter/(?P<pk>\d+)/show', generic_row, {'model':HealthProviderBase, 'partial_row':'cvs/reporter/partials/trainee_row.html'}),
    url(r'^cvs/reporter/new', reporters.newReporter),
    #url(r'^cvs/reporter/new',),


    #############################################
    #              FACILITY VIEWS               #
    #############################################
    url(r'^cvs/facility/$', login_required(generic), {
      'model':HealthFacilityBase,
      'queryset':get_facilites_for_view,
      'filter_forms':[],
      'action_forms':[],
      'objects_per_page':25,
      'partial_row':'cvs/facility/partials/facility_row.html',
      'base_template':'cvs/facility/facility_base.html',
      'results_title':'Health Facilities',
      'columns':[('Name', True, 'name', SimpleSorter()),
                 ('Type', True, 'type', SimpleSorter()),
                 ('Code', True, 'code', SimpleSorter(),),
                 ('District', False, 'district', None,),
                 ('Last Reporting Date', True, 'latest_submission', LatestFacilitySubmissionSorter(),),
                 ('Total Reports', True, 'submissions', TotalFacilitySubmissionSorter(),),
                 ('Catchment Areas', True, 'catchment_area__name', SimpleSorter(),),
                 ('', False, '', None,)],
      'sort_column':'latest_submission',
      'sort_ascending':False,
    }, name="cvs-facility"),

    url(r'^cvs/facility/(?P<facility_pk>\d+)/edit', facilities.editFacility),
    url(r'^cvs/facility/(?P<facility_pk>\d+)/locations/edit/((?P<district_pk>\d+)/)?', facilities.editFacilityLocations),
    url(r'^cvs/facility/(?P<facility_pk>\d+)/delete', facilities.deleteFacility),
    url(r'^cvs/facility/(?P<pk>\d+)/show', generic_row, {'model':HealthFacilityBase, 'partial_row':'cvs/facility/partials/facility_row.html'}),



    #############################################
    #              MESSAGE VIEWS                #
    #############################################
    url(r'^cvs/messagelog/$', login_required(generic), {
       'model':Message,
       'queryset':get_unsolicited_messages,
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

    url(r'^cvs/messagelogexample/$', login_required(generic), {
       'model':Message,
       'queryset':get_unsolicited_messages,
       'filter_forms':[FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
       'action_forms':[ReplyTextForm],
       'objects_per_page':50,
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
    },), #name="cvs-messagelog"),

    url(r'^cvs/allmessagelog/$', login_required(generic), {
       'model':Message,
       'queryset':get_all_messages,
       'filter_forms':[FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
       'action_forms':[ReplyTextForm],
       'objects_per_page':25,
       'partial_row':'contact/partials/message_row.html',
       'base_template':'cvs/all_messages_base.html',
       'columns':[('Text', True, 'text', SimpleSorter()),
                  ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
                  ('Date', True, 'date', SimpleSorter(),),
                  ('Type', True, 'application', SimpleSorter(),),
                  ('Response', False, 'response', None,),
                 ],
       'sort_column':'date',
       'sort_ascending':False,
    }, name="cvs-allmessages"),

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
    }, name="cvs-massmessages"),
   url(r'^cvs/train/messagelog/$', login_required(generic), {
      'model':Message,
      'queryset':get_training_messages,
      'filter_forms':[FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
      'action_forms':[ReplyTextForm],
      'objects_per_page':25,
      'partial_row':'contact/partials/message_row.html',
      'base_template':'cvs/training_messages_base.html',
      'columns':[('Text', True, 'text', SimpleSorter()),
                 ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
                 ('Date', True, 'date', SimpleSorter(),),
                 ('Type', True, 'application', SimpleSorter(),),
                 ('Response', False, 'response', None,),
                 ],
      'sort_column':'date',
      'sort_ascending':False,
    }, name="cvs-training-messagelog"),


    #############################################
    #              STATS VIEWS                  #
    #############################################
    (r'^cvs/stats/', include(MainReport().as_urlpatterns(name='stats'))),
    (r'^cvs/muac/', include(MuacReport().as_urlpatterns())),
    (r'^cvs/epi/', include(EpiReport().as_urlpatterns())),
    (r'^cvs/birth/', include(BirthReport().as_urlpatterns())),
    (r'^cvs/death/', include(DeathReport().as_urlpatterns())),
    (r'^cvs/home/', include(HomeReport().as_urlpatterns())),

    (r'^mtrack/stats/', include(MTrackReport().as_urlpatterns(name='mtrack-stats'))),
    (r'^mtrack/epi/', include(MTrackEpiReport().as_urlpatterns())),
    (r'^mtrack/birth/', include(MTrackBirthReport().as_urlpatterns())),
    (r'^mtrack/muac/', include(MTrackNutritionReport().as_urlpatterns())),
    (r'^mtrack/malaria/', include(MTrackMalariaReport().as_urlpatterns())),

    url(r'^cvs/data/excelexport/$', export_as_excel),

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
        'dates': XFormDateGetter().get_dates, \
        'display_autoload': False, \
    }, name="cvs-map"),

    url(r'^cvs/forms/$', login_required(generic), {
        'model':XForm,
        'objects_per_page':10,
        'selectable':False,
        'partial_row':'cvs/partials/form_row.html',
        'base_template':'cvs/xform_admin_base.html',
        'results_title':'Forms',
        'columns':[('Name', True, 'name', SimpleSorter()),
                 ('Description', True, 'description', SimpleSorter(),),
                 ('', False, '', None)],
    }, name="cvs-forms"),
    url(r"^cvs/forms/(\d+)/submissions/$", login_required(basic.view_submissions)),
)
