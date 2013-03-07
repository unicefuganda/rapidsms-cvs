from django import forms
import datetime
from healthmodels.models.HealthProvider import HealthProvider, \
    HealthProviderBase
from generic.forms import ActionForm, FilterForm
from healthmodels.models.HealthFacility import HealthFacility, HealthFacilityType
from mptt.forms import TreeNodeChoiceField
from rapidsms.contrib.locations.models import Location
from django.contrib.auth.models import Group
from mtrack.utils import get_district_for_facility
from rapidsms.models import Contact, Connection
from uganda_common.utils import assign_backend
from django.utils.translation import ugettext_lazy as _
from random import choice
from uganda_common.utils import get_location_for_user, get_districts_for_user
from django.conf import settings

date_range_choices = (('w', 'Previous Calendar Week'), ('m', 'Previous Calendar Month'), ('q', 'Previous calendar quarter'),)
AREAS = Location.tree.all().select_related('type')

class ActivateForm(ActionForm):

    action_label = 'Activate selected trainees'

    def perform(self, request, results):
        pks = []
        for r in results:
            pks.append(r.pk)
        Contact.objects.filter(pk__in=pks).update(active=True)
        return ('%d Contacts are now on the live system.' % len(results), 'success',)


class DeactivateForm(ActionForm):

    action_label = 'Deactivate selected reporters'

    def perform(self, request, results):
        pks = []
        for r in results:
            pks.append(r.pk)
        Contact.objects.filter(pk__in=pks).update(active=False)
        return ('%d Contacts are now deactivated.' % len(results), 'success',)


class ReporterForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    facility = forms.ModelChoiceField(queryset=HealthFacility.objects.all(), required=False)
    roles = forms.ModelMultipleChoiceField(queryset=Group.objects.all(), required=False)
    village_name = forms.CharField(max_length=100, required=False)
    reporter_district = forms.ModelChoiceField(queryset=Location.objects.filter(type__name='district').order_by('name'), empty_label='----', required=False, \
                                      widget=forms.Select({'onchange':'update_district(this)'}))
    reporting_location = forms.ModelChoiceField(queryset=Location.objects.all(), required=False)
    connection = forms.CharField(max_length=20, required=False,
                                 widget=forms.TextInput(attrs={'class':'itext', 'size':'10'}))

    def get_district(self):
        district = None
        if self.reporter.reporting_location or self.reporter.location:
            if self.reporter.reporting_location.type.name == 'district':
                district = self.reporter.reporting_location
            else:
                if self.reporter.reporting_location.get_ancestors().filter(type__name='district').count():
                    district = self.reporter.reporting_location.get_ancestors().filter(type__name='district')[0]
        return district

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        if 'instance' in kwargs:
            self.reporter = kwargs.pop('instance')
            if not 'data' in kwargs:
                initial = { \
                    'name':self.reporter.name, \
                    'roles':self.reporter.groups.all(), \
                    'facility':self.reporter.facility, \
                }
                district = self.get_district()
                if district:
                    initial.update({'reporter_district':district})
                kwargs.update({'initial':initial})
        else:
            self.reporter = None
        forms.Form.__init__(self, *args, **kwargs)
        self.fields['reporter_district'].queryset = get_districts_for_user(self.request.user)

    def clean_connection(self):
        connection = self.cleaned_data.get('connection')
        if not self.reporter and not connection.strip():
            raise forms.ValidationError(_("Connection is required for new reporters"))
        else:
            return connection

    def save(self):
        cleaned_data = self.cleaned_data
        district = cleaned_data.get('reporter_district')
        location = cleaned_data.get('reporting_location')
        connection = cleaned_data.get('connection')
        if connection:
            (identity, backend) = assign_backend(connection)
            connection, _x = Connection.objects.get_or_create(identity=identity, backend=backend)
            self.reporter.connection_set.add(connection)
        if district and location and \
            not district.get_descendants(include_self=True).filter(pk=location.pk).count():
            location = None
        self.reporter.location = self.reporter.reporting_location = location or district
        self.reporter.name = cleaned_data.get('name')
        self.reporter.groups.clear()
        for g in cleaned_data.get('roles'):
            self.reporter.groups.add(g)
        self.reporter.facility = cleaned_data.get('facility')
        if not location:
            self.reporter.village_name = cleaned_data.get('village_name')
        self.reporter.save()
        return


class FacilityFilterForm(FilterForm):
    """ filter form for cvs facilities """
    facility = forms.ChoiceField(label="Facility", choices=(('', '-----'),
                                                             (-1, 'Has No Facility'),) + tuple([(pk, '%s %s' % (name, type)) for pk, name, type in HealthFacility.objects.values_list('pk', 'name', 'type__name').order_by('type', 'name')]),
                                  widget=forms.Select({'class':'ffacility'}))


    def filter(self, request, queryset):
        facility_pk = self.cleaned_data['facility']
        if facility_pk == '':
            return queryset
        elif int(facility_pk) == -1:
            return queryset.filter(facility=None)
        else:
            return queryset.filter(facility_id=facility_pk)

class LastReportingFilter(FilterForm):
    last_reporting_date = forms.CharField(max_length=100, required=False)
    def filter(self, request, queryset):
        date = self.cleaned_data['last_reporting_date']
        if date == '':
            return queryset
        else:
            return queryset.filter(last_reporting_date__in=[date])

class FacilityDistrictFilter(FilterForm):

    """ filter cvs districs on their districts """
    districtx = forms.ChoiceField(label="District", choices=(('', 'No District'),) + tuple([(d.name,
                                 d.name) for d in
                                 Location.objects.filter(type__slug='district'
                                 ).order_by('name')]), required=False,)

    def filter(self, request, queryset):
        district_name = self.cleaned_data['districtx']
        if district_name == '':
            return queryset
        else:
            return queryset.filter(district=district_name)

class FacilityResponseForm(forms.Form):
    def __init__(self, data=None, **kwargs):
        response = kwargs.pop('response')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)

    value = forms.ModelChoiceField(queryset=HealthFacility.objects.order_by('name'))

OWNERS = (
          ('', '-----'),
          ('GOVT', 'Government'),
          ('NGO', 'NGO'),
          ('PRIVATE', 'Private'),
          )
AUTHORITIES = (
               ('', '-------'),
               ('AIDS PROG', 'AIDS PROG'),
               ('COMMUNITY', 'COMMUNITY'),
               ('CSO', 'CSO'),
               ('GTZ', 'GTZ'),
               ('HOSFA', 'HOSFA'),
               ('MAP', 'MAP'),
               ('MSU', 'MSU'),
               ('OTHER NGO', 'OTHER NGO'),
               ('PRIVATE', 'PRIVATE'),
               ('RH UGANDA', 'RH UGANDA'),
               ('RHU', 'RHU'),
               ('SDA', 'SDA'),
               ('TEA FACTORY', 'TEA FACTORY'),
               ('TOURISM', 'TOURISM'),
               ('UCBM', 'UCBM'),
               ('UG. CLAYS', 'UG. CLAYS'),
               ('UMMB', 'UMMB'),
               ('UNHCR', 'UNHCR'),
               ('UPMB', 'UPMB'),
               ('WORLD VISION', 'WORLD VISION'),
               )

class FacilityForm(forms.Form):
    name = forms.CharField(max_length=100, required=getattr(settings, 'ALLOW_BLANK_HEALTHFACILITY', True))
    code = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'size':14}))
    type = forms.ModelChoiceField(queryset=HealthFacilityType.objects.all(), required=True)
    catchment_areas = forms.ModelMultipleChoiceField(queryset=Location.objects.all(), required=False)
    owner = forms.ChoiceField(choices=OWNERS, required=False)
    authority = forms.ChoiceField(choices=AUTHORITIES, required=False)
    def __init__(self, *args, **kwargs):
        self.username = kwargs.pop('username', '')
        if 'instance' in kwargs:
            self.facility = kwargs.pop('instance')
            if not 'data' in kwargs:
                initial = { \
                    'name':self.facility.name, \
                    'code':self.facility.code, \
                    'type':self.facility.type, \
                    'owner':self.facility.owner, \
                    'authority':self.facility.authority, \
                    'catchment_areas':self.facility.catchment_areas.all(), \
                }
                district = get_district_for_facility(self.facility)
                if district:
                    initial.update({'facility_district':district})
                kwargs.update({'initial':initial})
        else:
            chars = '1234567890_QWERTYUOPASDFGHJKLZXCVBNM'
            self.code = u"gen" + u"".join([choice(chars) \
                                          for i in range(10)]).lower()
            initial = {'code':self.code}
            kwargs.update({'initial':initial})
            self.facility = None
        forms.Form.__init__(self, *args, **kwargs)
        self.fields['facility_district'] = forms.ModelChoiceField(queryset=self.get_districts_for_form(self.username), empty_label='----', required=False, \
                                      widget=forms.Select({'onchange':'update_facility_district(this)'}))


    def get_districts_for_form(self, user):
        loc = Location.objects.filter(name=str(user).capitalize(), type__name='district')
        if loc:
            return loc
        else:
            return Location.objects.filter(type__name='district').order_by('name')
    def save(self):
        cleaned_data = self.cleaned_data
        if cleaned_data.get('facility_district'):
            district = cleaned_data.get('facility_district').name
        else:
            district = ""
        if not self.facility:
            self.facility = HealthFacility.objects.create(
                                                          name=cleaned_data.get('name'),
                                                          code=cleaned_data.get('code'),
                                                          type=cleaned_data.get('type'),
                                                          district=district,
                                                          owner=cleaned_data.get('owner'),
                                                          authority=cleaned_data.get('authority')
                                                          )
        else:
            self.facility.name = cleaned_data.get('name')
            self.facility.code = cleaned_data.get('code')
            self.facility.type = cleaned_data.get('type')
            self.facility.district = district
            self.facility.owner = cleaned_data.get('owner')
            self.facility.authority = cleaned_data.get('authority')
        self.facility.save()

        self.facility.catchment_areas.clear()
        for c in cleaned_data.get('catchment_areas'):
            self.facility.catchment_areas.add(c)
        return

