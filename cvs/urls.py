from django.conf.urls.defaults import *
from django.contrib.auth.decorators import login_required
from cvs.views import basic, reporters, map, facilities, ajax_upload
from generic.views import generic, generic_row, generic_map
from generic.sorters import SimpleSorter, TupleSorter
from contact.forms import FreeSearchForm2, MassTextForm
from mtrack.forms import DistrictFilterForm, RolesFilter, PhaseFilter, FacilityFilterForm
from cvs.forms import ActivateForm, DeactivateForm, LastReportingFilter, FacilityDistrictFilter
from cvs.utils import get_reporters
from cvs.sorters import \
    LatestSubmissionSorter
from rapidsms.contrib.locations.models import Location
from uganda_common.reports import XFormDateGetter
from cvs.views.stats import export_as_excel
from healthmodels.models.HealthProvider import HealthProviderBase


from rapidsms_xforms.models import XForm
from cvs.utils import get_all_messages, get_unsolicited_messages, get_training_messages, get_nolocation_vhts, get_training_vhts, get_dashboard_messages
from mtrack.utils import get_facilites_for_view, get_location_mass_messages
from mtrack.models import Facilities, Reporters
from cvs.reports import HomeReport, DeathReport, BirthReport, EpiReport, MuacReport, MainReport, MTrackMalariaReport, MTrackNutritionReport, MTrackBirthReport, MTrackEpiReport, MTrackReport
from rapidsms_httprouter.models import Message
from contact.models import MassText
from contact.forms import FreeSearchTextForm, DistictFilterMessageForm, HandledByForm, ReplyTextForm
from cvs.paginator import mtrac_paginate


urlpatterns = patterns('',
                       #############################################
                       #              REPORTERS VIEWS              #
                       #############################################
                       # Registered Users
                       url(r'^cvs/reporter/$', login_required(generic), {
                           'model': Reporters,
                           'queryset': get_reporters,
                           'filter_forms': [FreeSearchForm2, DistrictFilterForm, RolesFilter, LastReportingFilter,
                                            FacilityFilterForm, PhaseFilter],
                           'action_forms': [MassTextForm, DeactivateForm],
                           'objects_per_page': 25,
                           'partial_row': 'cvs/reporter/partials/reporter_row2.html',
                           'partial_header': 'cvs/reporter/partials/partial_header.html',
                           'base_template': 'cvs/reporter/registered_contacts.html',
                           'paginator_template': 'cvs/partials/new_pagination.html',
                           'results_title': 'Registered Users',
                           'columns': [('Name', True, 'name', SimpleSorter()),
                                       ('Number', True, 'connections', SimpleSorter(),),
                                       ('Role(s)', True, 'groups', SimpleSorter(),),
                                       ('District', True, 'district', SimpleSorter(),),
                                       ('Last Reporting Date', True, 'last_reporting_date', LatestSubmissionSorter(),),
                                       ('Total Reports', True, 'total_reports', SimpleSorter(),),
                                       ('Facility', True, 'facility', SimpleSorter(),),
                                       ('Location', True, 'loc_name', SimpleSorter(),),
                                       ('Active', True, 'active', SimpleSorter(),),
                                       ('', False, '', None,)],
                           'sort_column': 'last_reporting_date',
                           'sort_ascending': False,
                           'paginator_func': mtrac_paginate,
                           'districts': [d.upper() for d in
                                         Location.objects.filter(type='district').values_list('name', flat=True)]
                       }, name="cvs-contact"),
                       # Trainees
                       url(r'^cvs/train/reporter/$', login_required(generic), {
                           'model': Reporters,
                           'queryset': get_training_vhts,
                           'filter_forms': [FreeSearchForm2, FacilityFilterForm, RolesFilter, DistrictFilterForm],
                           'action_forms': [MassTextForm, ActivateForm],
                           'objects_per_page': 25,
                           'partial_row': 'cvs/reporter/partials/trainee_row.html',
                           'base_template': 'cvs/reporter/training_contacts.html',
                           'paginator_template': 'cvs/partials/new_pagination.html',
                           'results_title': 'Trainees',
                           'sort_column': 'last_reporting_date',
                           'sort_ascending': False,
                           'paginator_func': mtrac_paginate,
                           'columns': [('Name', True, 'name', SimpleSorter()),
                                       ('Number', True, 'connections', SimpleSorter(),),
                                       ('Role(s)', True, 'groups', SimpleSorter(),),
                                       ('District', True, 'district', SimpleSorter(),),
                                       ('Last Reporting Date', True, 'last_reporting_date', LatestSubmissionSorter(),),
                                       ('Total Reports', True, 'total_reports', SimpleSorter(),),
                                       ('Facility', True, 'facility', SimpleSorter(),),
                                       ('Location', True, 'loc_name', SimpleSorter(),),
                                       ('Active', False, '', None,),
                                       ('', False, '', None,)],
                       }, name="cvs-training-contact"),
                       # Orphaned
                       url(r'^cvs/orphaned/reporter/$', login_required(generic), {
                           'model': HealthProviderBase,
                           'queryset': get_nolocation_vhts,
                           'filter_forms': [FreeSearchForm2, FacilityFilterForm],
                           'action_forms': [MassTextForm, ActivateForm],
                           'objects_per_page': 25,
                           'partial_row': 'cvs/reporter/partials/reporter_row.html',
                           'base_template': 'cvs/reporter/nolocation_contacts.html',
                           'paginator_template': 'cvs/partials/new_pagination.html',
                           'results_title': 'No Location',
                           'sort_column': 'join_date',
                           'sort_ascending': False,
                           'paginator_func': mtrac_paginate,
                           'columns': [('Name', True, 'name', SimpleSorter()),
                                       ('Number', True, 'connection__identity', SimpleSorter(),),
                                       ('Role(s)', True, 'groups__name', SimpleSorter(),),
                                       ('District', False, 'district', None,),
                                       ('Last Reporting Date', True, 'last_reporting_date', LatestSubmissionSorter(),),
                                       ('Total Reports', True, 'connection__submissions__count', SimpleSorter(),),
                                       ('Facility', True, 'facility__name', SimpleSorter(),),
                                       ('Location', True, 'location__name', SimpleSorter(),),
                                       ('', False, '', None,)],
                       }, name="cvs-orphan-contact"),

                       url(r'^cvs/((train|orphaned)/)?reporter/(?P<reporter_pk>\d+)/edit', reporters.editReporter),
                       url(
                           r'^cvs/((train|orphaned)/)?reporter/(?P<reporter_pk>\d+)/locations/edit/((?P<district_pk>\d+)/)?',
                           reporters.editReporterLocations),
                       url(r'^cvs/((train|orphaned)/)?reporter/locations/edit/((?P<district_pk>\d+)/)?',
                           reporters.editReporterLocations),
                       url(
                           r'^cvs/((train|orphaned)/)?reporter/((?P<reporter_pk>\d+)/)?facilities/edit/((?P<district_pk>\d+)/)?((?P<district>\w+)/)?',
                           reporters.editReporterFacilities),
                       # url(r'^cvs/((train|orphaned)/)?reporter/facilities/edit/((?P<district_pk>\d+)/)?', reporters.editReporterFacilities),
                       url(r'^cvs/((train|orphaned)/)?reporter/(?P<reporter_pk>\d+)/delete', reporters.deleteReporter),
                       url(r'^cvs/(orphaned/)?reporter/(?P<pk>\d+)/show', generic_row,
                           {'model': Reporters, 'partial_row': 'cvs/reporter/partials/reporter_row2.html'}),
                       url(r'^cvs/train/reporter/(?P<pk>\d+)/show', generic_row,
                           {'model': Reporters, 'partial_row': 'cvs/reporter/partials/trainee_row.html'}),
                       url(r'^cvs/reporter/new', login_required(reporters.newReporter)),
                       # url(r'^cvs/reporter/new',),
                       url(r'^ajax_upload/$', ajax_upload.ajax_upload, name="ajax_upload"),


                       #############################################
                       #              FACILITY VIEWS               #
                       #############################################
                       url(r'^cvs/facility/$', login_required(generic), {
                           'model': Facilities,
                           'queryset': get_facilites_for_view,
                           'filter_forms': [FacilityDistrictFilter],
                           'action_forms': [],
                           'objects_per_page': 25,
                           'partial_row': 'cvs/facility/partials/facility_row.html',
                           'partial_header': 'cvs/facility/partials/partial_header.html',
                           'base_template': 'cvs/facility/facility_base.html',
                           'paginator_template': 'cvs/partials/new_pagination.html',
                           'results_title': 'Health Facilities',
                           'columns': [('Name', True, 'name', SimpleSorter()),
                                       ('Type', True, 'type', SimpleSorter()),
                                       # ('Code', True, 'code', SimpleSorter(),),
                                       ('District', True, 'district', SimpleSorter(),),
                                       ('Last Reporting Date', True, 'last_reporting_date', LatestSubmissionSorter(),),
                                       ('Owner', True, 'owner', SimpleSorter(),),
                                       # ('Total Reports', True, 'total_reports', SimpleSorter()),
                                       # TotalFacilitySubmissionSorter(),),
                                       # ('Catchment Areas', True, 'catchment_areas', SimpleSorter()),  # __name', SimpleSorter(),),
                                       ('Has Complete Rpt', False, '', SimpleSorter(),),
                                       ('', False, '', None,)],
                           'sort_column': 'last_reporting_date',
                           'sort_ascending': False,
                           'paginator_func': mtrac_paginate,
                       }, name="cvs-facility"),

                       url(r'^cvs/facility/(?P<facility_pk>\d+)/edit', login_required(facilities.editFacility)),
                       url(r'^cvs/facility/(?P<facility_pk>\d+)/locations/edit/((?P<district_pk>\d+)/)?',
                           facilities.editFacilityLocations),
                       url(r'^cvs/facility/locations/new/((?P<district_pk>\d+)/)?', login_required(facilities.editFacilityLocations)),
                       url(r'^cvs/facility/(?P<facility_pk>\d+)/delete', login_required(facilities.deleteFacility)),
                       url(r'^cvs/facility/(?P<pk>\d+)/show', generic_row,
                           {'model': Facilities, 'partial_row': 'cvs/facility/partials/facility_row.html'}),
                       url(r'^cvs/facility/new', login_required(facilities.newFacility)),
                       url(r'^cvs/facility/(?P<facility_pk>\d+)/detail/', login_required(facilities.facilityDetails), name='facility-details'),
                       url(r'^cvs/facility/(?P<facility_pk>\d+)/completeness/', login_required(facilities.facilityReportCompleteness), name='facility-report-completeness'),
                       url(r'^cvs/facility/(?P<facility_pk>\d+)/sendsms/', login_required(facilities.sendSMS), name='facility-sendsms'),
                       url(r'^cvs/facility/reports/(?P<facility_pk>\d+)/', login_required(facilities.get_facility_reports),
                           name="facility_reports"),

                       #############################################
                       #              MESSAGE VIEWS                #
                       #############################################
                       url(r'^cvs/messagelog/$', login_required(generic), {
                           'model': Message,
                           'queryset': get_unsolicited_messages,
                           'filter_forms': [FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
                           'action_forms': [ReplyTextForm],
                           'objects_per_page': 25,
                           'partial_row': 'contact/partials/message_row.html',
                           'paginator_template': 'cvs/partials/new_pagination.html',
                           'base_template': 'cvs/messages_base.html',
                           'columns': [('Text', True, 'text', SimpleSorter()),
                                       ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
                                       ('Date', True, 'date', SimpleSorter(),),
                                       ('Type', True, 'application', SimpleSorter(),),
                                       ('Response', False, 'response', None,),
                           ],
                           'sort_column': 'date',
                           'paginator_func': mtrac_paginate,
                           'sort_ascending': False,
                       }, name="cvs-messagelog"),

                       url(r'^cvs/messagelogexample/$', login_required(generic), {
                           'model': Message,
                           'queryset': get_unsolicited_messages,
                           'filter_forms': [FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
                           'action_forms': [ReplyTextForm],
                           'objects_per_page': 50,
                           'partial_row': 'contact/partials/message_row.html',
                           'base_template': 'cvs/messages_base.html',
                           'columns': [('Text', True, 'text', SimpleSorter()),
                                       ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
                                       ('Date', True, 'date', SimpleSorter(),),
                                       ('Type', True, 'application', SimpleSorter(),),
                                       ('Response', False, 'response', None,),
                           ],
                           'sort_column': 'date',
                           'sort_ascending': False,
                       },),  # name="cvs-messagelog"),

                       url(r'^cvs/allmessagelog/$', login_required(generic), {
                           'model': Message,
                           'queryset': get_all_messages,
                           'filter_forms': [FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
                           'action_forms': [ReplyTextForm],
                           'objects_per_page': 25,
                           'partial_row': 'contact/partials/message_row.html',
                           'base_template': 'cvs/all_messages_base.html',
                           'paginator_template': 'cvs/partials/new_pagination.html',
                           'columns': [('Text', True, 'text', SimpleSorter()),
                                       ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
                                       ('Date', True, 'date', SimpleSorter(),),
                                       ('Type', True, 'application', SimpleSorter(),),
                                       ('Response', False, 'response', None,),
                           ],
                           'sort_column': 'date',
                           'sort_ascending': False,
                           'paginator_func': mtrac_paginate,
                       }, name="cvs-allmessages"),

                       url(r'^cvs/massmessages/$', login_required(generic), {
                           'model': MassText,
                           'queryset': get_location_mass_messages,
                           'objects_per_page': 10,
                           'partial_row': 'contact/partials/mass_message_row.html',
                           'paginator_template': 'cvs/partials/new_pagination.html',
                           'base_template': 'cvs/mass_messages_base.html',
                           'columns': [('Message', True, 'text', TupleSorter(0)),
                                       ('Time', True, 'date', TupleSorter(1),),
                                       ('Sender', True, 'user', TupleSorter(2),),
                                       ('Recipients', True, 'count', TupleSorter(3),),
                           ],
                           'sort_column': 'date',
                           'sort_ascending': False,
                           'paginator_func': mtrac_paginate,
                           'selectable': False,
                       }, name="cvs-massmessages"),
                       url(r'^cvs/train/messagelog/$', login_required(generic), {
                           'model': Message,
                           'queryset': get_training_messages,
                           'filter_forms': [FreeSearchTextForm, DistictFilterMessageForm, HandledByForm],
                           'action_forms': [ReplyTextForm],
                           'objects_per_page': 25,
                           'partial_row': 'contact/partials/message_row.html',
                           'base_template': 'cvs/training_messages_base.html',
                           'paginator_template': 'cvs/partials/new_pagination.html',
                           'columns': [('Text', True, 'text', SimpleSorter()),
                                       ('Contact Information', True, 'connection__contact__name', SimpleSorter(),),
                                       ('Date', True, 'date', SimpleSorter(),),
                                       ('Type', True, 'application', SimpleSorter(),),
                                       ('Response', False, 'response', None,),
                           ],
                           'sort_column': 'date',
                           'sort_ascending': False,
                           'paginator_func': mtrac_paginate,
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

                       (r'^mtrack/stats/',
                        include(MTrackReport().as_urlpatterns(name='mtrack-stats', login_wrapper=login_required))),
                       (r'^mtrack/epi/', include(MTrackEpiReport().as_urlpatterns())),
                       (r'^mtrack/birth/', include(MTrackBirthReport().as_urlpatterns())),
                       (r'^mtrack/muac/', include(MTrackNutritionReport().as_urlpatterns())),
                       (r'^mtrack/malaria/', include(MTrackMalariaReport().as_urlpatterns())),

                       url(r'^cvs/data/excelexport/$', export_as_excel),

                       # map API calls
                       url(
                           r'^cvs/stats/(?P<start_date>\d+)/(?P<end_date>\d+)/(?P<xform_keyword>[a-z]+)/((?P<attribute_keyword>[a-zA-Z_]+)/)?',
                           map.map_api),
                       url(r'^cvs/stats/(?P<start_date>\d+)/(?P<end_date>\d+)/2/epi/other/', map.map_other_api),
                       url(r'^cvs/stats/healthfacility', map.health_facility_api),

                       # map view
                       url(r'^cvs/map/', generic_map, {
                           'map_layers': [
                               {'name': 'Health Facilities', 'url': '/cvs/stats/healthfacility', 'autoload': True},
                               {'name': 'Malnutrition', 'url': '/cvs/stats/<start_ts>/<end_ts>/muac/',
                                'color': '#80699B', 'needs_date': True},
                               {'name': 'Deaths', 'url': '/cvs/stats/<start_ts>/<end_ts>/death/', 'color': '#AA4643',
                                'needs_date': True},
                               {'name': 'Births', 'url': '/cvs/stats/<start_ts>/<end_ts>/birth/', 'color': '#89A54E',
                                'needs_date': True},
                               {'name': 'Malaria', 'url': '/cvs/stats/<start_ts>/<end_ts>/epi/ma/', 'color': '#3D96AE',
                                'needs_date': True},
                               {'name': 'Dysentery', 'url': '/cvs/stats/<start_ts>/<end_ts>/epi/bd/',
                                'color': '#DB843D', 'needs_date': True},
                               {'name': 'Tuberculosis', 'url': '/cvs/stats/<start_ts>/<end_ts>/epi/tb/',
                                'color': '#92A8CD', 'needs_date': True},
                               {'name': 'Other Diseases', 'url': '/cvs/stats/<start_ts>/<end_ts>/2/epi/other/',
                                'color': '#A47D7C', 'needs_date': True},
                           ],
                           'dates': XFormDateGetter().get_dates, \
                           'display_autoload': False, \
                           }, name="cvs-map"),

                       url(r'^cvs/forms/$', login_required(generic), {
                           'model': XForm,
                           'objects_per_page': 10,
                           'selectable': False,
                           'partial_row': 'cvs/partials/form_row.html',
                           'base_template': 'cvs/xform_admin_base.html',
                           'results_title': 'Forms',
                           'columns': [('Name', True, 'name', SimpleSorter()),
                                       ('Description', True, 'description', SimpleSorter(),),
                                       ('', False, '', None)],
                       }, name="cvs-forms"),
                       url(r"^cvs/forms/(\d+)/submissions/$", login_required(basic.view_submissions)),
)

