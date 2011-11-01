from healthmodels.models import *
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from healthmodels.models.HealthFacility import HealthFacility
from healthmodels.models.HealthProvider import HealthProvider
from rapidsms.contrib.locations.models import Location
from django.views.decorators.cache import cache_control
from django.http import HttpResponseRedirect, HttpResponse
from cvs.utils import ExcelResponse
from cvs.views.dates import get_expected_epi
from uganda_common.forms import DateRangeForm
import datetime
import time
from django.utils.datastructures import SortedDict
from rapidsms_xforms.models import XFormSubmission, XFormSubmissionValue
from rapidsms.models import Contact
import re
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum


def get_district(lst, lft, rght):
    "get a district name give a location's rght and lft"
    for d in lst:
        if d[1][0] <= lft and d[1][1] >= rght:
            return d[0]


def export_as_excel(request):
    submissions = XFormSubmission.objects.select_related('connection', 'connection__identity', 'connection__contact', 'connection__contact__name').all()
    health_providers = HealthProvider.objects.select_related('location', 'facility', 'location__name', 'facility__name', 'location__lft', 'loction__rght')
    export_data_list = []
    districts = []
    for d in Location.objects.filter(type__slug='district'):
        districts.append((d.name, [d.lft, d.rght]))
    for submission in submissions:
        export_data = SortedDict()
        if submission.connection.contact:
            export_data['reporter_name'] = submission.connection.contact.name
        else:
            export_data['reporter_name'] = ''

        export_data['reporter_number'] = submission.connection.identity
        if submission.connection.contact:
            try:
                loc = health_providers.filter(contact_ptr=submission.connection.contact.pk)[0].location
                export_data['location'] = loc.name
                export_data['district'] = get_district(districts, loc.lft, loc.rght)
            except:
                export_data['location'] = ''
                export_data['district'] = ''
        else:
             export_data['location'] = ''
             export_data['district'] = ''

        export_data['time'] = str(submission.created)
        if submission.connection.contact :
            try:
                export_data['facility'] = health_providers.filter(contact_ptr=submission.connection.contact)[0].facility.name
            except:
                export_data['facility'] = ''

        else:
            export_data['facility'] = ''
        export_data['message'] = submission.raw
        data = {}
        for d in submission.values.all():
            data[d.attribute.slug] = d.value
        export_data['report_keyword'] = submission.xform.keyword
        export_data['muac_name'] = data.get('muac_name', '')
        export_data['muac_gender'] = data.get('muac_gender', '')
        export_data['muac_age'] = data.get('muac_age', '')
        export_data['muac_category'] = data.get('muac_category', '')
        export_data['muac_eodema'] = data.get('muac_eodema', '')
        export_data['home_it'] = data.get('home_it', '')
        export_data['home_to'] = data.get('home_to', '')
        export_data['home_la'] = data.get('home_la', '')
        export_data['home_ha'] = data.get('home_ha', '')
        export_data['home_wa'] = data.get('home_wa', '')
        export_data['death_name'] = data.get('death_name', '')
        export_data['death_gender'] = data.get('death_gender', '')
        export_data['death_age'] = data.get('death_age', '')
        export_data['birth_name'] = data.get('birth_name', '')
        export_data['birth_place'] = data.get('birth_place', '')
        export_data['birth_gender'] = data.get('birth_gender', '')
        export_data['epi_ma'] = data.get('epi_ma', '')
        export_data['epi_bd'] = data.get('epi_bd', '')
        export_data['epi_tb'] = data.get('epi_tb', '')
        export_data['epi_ab'] = data.get('epi_ab', '')
        export_data['epi_af'] = data.get('epi_af', '')
        export_data['epi_mg'] = data.get('epi_mg', '')
        export_data['epi_me'] = data.get('epi_me', '')
        export_data['epi_ch'] = data.get('epi_ch', '')
        export_data['epi_gw'] = data.get('epi_gw', '')
        export_data['epi_nt'] = data.get('epi_nt', '')
        export_data['epi_yf'] = data.get('epi_yf', '')
        export_data['epi_pl'] = data.get('epi_pl', '')
        export_data['epi_ra'] = data.get('epi_ra', '')
        export_data['epi_vf'] = data.get('epi_vf', '')
        export_data['epi_ei'] = data.get('epi_ei', '')
        export_data_list.append(export_data)

    return ExcelResponse(export_data_list)

