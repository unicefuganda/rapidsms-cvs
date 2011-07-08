from django import forms
import datetime
from healthmodels.models.HealthProvider import HealthProvider
from generic.forms import ActionForm, FilterForm, ModuleForm
from healthmodels.models.HealthFacility import HealthFacility
from mptt.forms import TreeNodeChoiceField
from rapidsms.contrib.locations.models import Location

date_range_choices=(('w','Previous Calendar Week'),('m','Previous Calendar Month'),('q','Previous calendar quarter'),)
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

AREAS = Location.tree.all().select_related('type')

class EditReporterForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        global AREAS
        super(EditReporterForm, self).__init__(*args, **kwargs)
        len(AREAS)
        self.fields['location'] = TreeNodeChoiceField(queryset=AREAS, level_indicator=u'.',required=False, empty_label='----')

    class Meta:
        model=HealthProvider
        fields = ('name', 'facility', 'location')

class FacilityFilterForm(FilterForm):
    """ filter form for cvs facilities """
    facility=forms.ChoiceField(choices=(('','-----'),(-1,'Has No Facility'),)+tuple([(int(f.pk),f.name) for f in HealthFacility.objects.all().order_by('type','name') ]))
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

class ChartModuleForm(ModuleForm):
    type=forms.ChoiceField(choices=(
        ('epi___ma','Variation of Malaria reports'),
        ('epi___tb','Variation of Tuberculosis reports'),
        ('epi___bd','Variation of Bloody Diarrhea reports'),
        ('muac','Variation of Malnutrition reports'),
        ('birth','Variation of Birth reports'),
        ('birth___gender___M','Variation of male birth reports'),
        ('birth___gender___F','Variation of female birth reports'),
        ('death','Variation of Death reports'),
        ('home___wa___percentage', 'Variation of Homesteads with safe drinking water'),
        ('epi___percentage', 'Variation of percentage of expected weekly epi reports received'),
    ), label="Data to chart")
    title = forms.CharField(max_length=40)
    district = forms.ModelChoiceField(queryset=Location.objects.filter(type__slug='district').order_by('name'))
    range=forms.ChoiceField(choices= date_range_choices,label="date Range")

    def setModuleParams(self, dashboard, module=None, title=None):
        module = module or self.createModule(dashboard, 'cvs.views.chart.chart', title=title)

        module.params.create(module=module, param_name='location_id', param_value=str(self.cleaned_data['district'].pk), is_url_param=True)
        module.params.create(module=module, param_name='date_range', param_value=str(self.cleaned_data['range']), is_url_param=False)
        param_list = self.cleaned_data['type'].split('___')
        if len(param_list) > 0:
            module.params.create(module=module, param_name='xform_keyword', param_value=param_list[0], is_url_param=True)
        if len(param_list) > 1:
            module.params.create(module=module, param_name='attribute_keyword', param_value=param_list[1], is_url_param=True)
        if len(param_list) > 2:
            module.params.create(module=module, param_name='attribute_value', param_value=param_list[2], is_url_param=True)

        return module


class MapModuleForm(ModuleForm):
    layer = forms.ChoiceField(choices=(
    ('health_facilities', 'health Facilities'),
    ('malnutrition', 'Malnutrition'),
    ('deaths', 'Deaths'),
    ('epi__other', 'other_epi'),
    ('births', 'Births'),
    ('epi__ma', 'Malaria'),
    ('epi__bd', 'Bloody  Diarrhoea'),
    ('epi__tb', 'TuberClosis'),
    ('epi__tb', 'TuberClosis'),
    ), label="Layers To Map ")
    title=forms.CharField(max_length=40)
    range=forms.ChoiceField(choices= date_range_choices,label="date Range")
    def setModuleParams(self, dashboard, module=None,title=None):
        if len(self.cleaned_data['title'])>0:
            title=self.cleaned_data['title']
        module = module or self.createModule(dashboard, 'cvs.views.map.map_index',title=title)
        module.params.create(module=module, param_name='date_range', param_value=str(self.cleaned_data['range']), is_url_param=False)
        module.params.create(module=module, param_name='range', param_value=str(self.cleaned_data['range']), is_url_param=False)
        param_list = self.cleaned_data['layer'].split('__')
        if len(param_list) > 0:
            module.params.create(module=module, param_name='layer', param_value=param_list[0], is_url_param=True)
        if len(param_list) > 1:
            module.params.create(module=module, param_name='kind', param_value=param_list[1], is_url_param=True)

        return module

    
class StatsModuleForm(ModuleForm):
    type=forms.ChoiceField(choices=(
        ('epi_detail','Variation of EPI reports'),
        ('muac_detail','Variation of Malnutrition reports'),
        ('birth_detail','Variation of Birth reports'),
        ('death_detail','Variation of Death reports'),
        ('home_detail', 'Variation of Homesteads reports'),
    ), label="Statistics to Show")
    title = forms.CharField(max_length=40)
    root_node = Location.tree.root_nodes()[0]
    district = forms.ChoiceField(choices=(('', '----------'), (int(root_node.pk),
                                 'All Districts')) + tuple([(int(d.pk),
                                 d.name) for d in
                                 Location.objects.filter(type__slug='district'
                                 ).order_by('name')]))
    range=forms.ChoiceField(choices= date_range_choices,label="date Range")
    def setModuleParams(self, dashboard, module=None, title=None):
        module = module or self.createModule(dashboard, 'cvs.views.stats.module_stats', title=title)
        module.params.create(module=module, param_name='date_range', param_value=str(self.cleaned_data['range']), is_url_param=False)
        module.params.create(module=module, param_name='location_id', param_value=str(self.cleaned_data['district']), is_url_param=True)
        module.params.create(module=module, param_name='view_name', param_value=self.cleaned_data['type'], is_url_param=True)

        return module
