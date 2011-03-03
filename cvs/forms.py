from django import forms
import datetime
from healthmodels.models.HealthProvider import HealthProvider
from generic.forms import ActionForm, FilterForm
from healthmodels.models.HealthFacility import HealthFacility

class DateRangeForm(forms.Form): # pragma: no cover
    start_ts = forms.IntegerField(required=True, widget=forms.HiddenInput())
    end_ts = forms.IntegerField(required=True, widget=forms.HiddenInput())

    def clean(self):
        cleaned_data = self.cleaned_data

        start_ts = cleaned_data.get('start_ts')
        cleaned_data['start_ts'] = datetime.datetime.fromtimestamp(float(start_ts) / 1000.0)

        end_ts = cleaned_data.get('end_ts')
        cleaned_data['end_ts'] = datetime.datetime.fromtimestamp(float(end_ts) / 1000.0)
        return cleaned_data

class EditReporterForm(forms.ModelForm):
    class Meta:
        model=HealthProvider

class FacilityFilterForm(FilterForm):
    """ filter form for cvs facilities """
    facility=forms.ChoiceField(choices=(('','-----'),)+((-1,'Has No Facility'),)+tuple([(int(f.pk),f.name) for f in HealthFacility.objects.all() ]))
    def filter(self, request, queryset):
        facility_pk = self.cleaned_data['facility']
        if facility_pk == '':
            return queryset
        elif int(facility_pk) == -1:
            return queryset.filter(facility=None)
        else:
            return queryset.filter(facility=facility_pk)





