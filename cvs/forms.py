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
        Contact.objects.filter(pk__in=pks).update(active=True)
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
    facility = forms.ChoiceField(choices=(('', '-----'), (-1, 'Has No Facility'),) + tuple(HealthFacility.objects.values_list('pk', 'name').order_by('type', 'name')))


    def filter(self, request, queryset):
        facility_pk = self.cleaned_data['facility']
        if facility_pk == '':
            return queryset
        elif int(facility_pk) == -1:
            return queryset.filter(facility=None)
        else:
            return queryset.filter(facility=facility_pk)

class FacilityResponseForm(forms.Form):
    def __init__(self, data=None, **kwargs):
        response = kwargs.pop('response')
        if data:
            forms.Form.__init__(self, data, **kwargs)
        else:
            forms.Form.__init__(self, **kwargs)

    value = forms.ModelChoiceField(queryset=HealthFacility.objects.order_by('name'))


class FacilityForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    code = forms.CharField(max_length=50, required=False)
    type = forms.ModelChoiceField(queryset=HealthFacilityType.objects.all(), required=True)
    catchment_areas = forms.ModelMultipleChoiceField(queryset=Location.objects.all(), required=False)
    facility_district = forms.ModelChoiceField(queryset=Location.objects.filter(type__name='district').order_by('name'), empty_label='----', required=False, \
                                      widget=forms.Select({'onchange':'update_facility_district(this)'}))

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            self.facility = kwargs.pop('instance')
            if not 'data' in kwargs:
                initial = { \
                    'name':self.facility.name, \
                    'code':self.facility.code, \
                    'type':self.facility.type, \
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

    def save(self):
        cleaned_data = self.cleaned_data
        if not self.facility:
            self.facility = HealthFacility.objects.create(
                                                          name=cleaned_data.get('name'),
                                                          code=cleaned_data.get('code'),
                                                          type=cleaned_data.get('type'))
        else:
            self.facility.name = cleaned_data.get('name')
            self.facility.code = cleaned_data.get('code')
            self.facility.type = cleaned_data.get('type')
        self.facility.save()

        self.facility.catchment_areas.clear()
        for c in cleaned_data.get('catchment_areas'):
            self.facility.catchment_areas.add(c)
        return

