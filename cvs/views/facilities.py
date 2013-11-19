#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.template import RequestContext
from django.shortcuts import (render_to_response, get_object_or_404)
from django.http import HttpResponse
from healthmodels.models.HealthFacility import HealthFacility, \
    HealthFacilityBase, HealthFacilityType
from healthmodels.models.HealthProvider import HealthProvider
from cvs.forms import FacilityForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from generic.views import generic_row
from rapidsms.contrib.locations.models import Location
from rapidsms_httprouter.models import Message
from rapidsms.models import Connection
from mtrack.utils import get_district_for_facility, last_reporting_period
from mtrack.models import Facilities, XFormSubmissionExtras
# from cvs.views.facilities import facility_form
from django.views.decorators.cache import cache_page
from django.db import transaction
from django.conf import settings
from django.utils import simplejson
from cvs.paginator import mtrac_paginate
from generic.views import generic

@login_required
def deleteFacility(request, facility_pk):
    facility = get_object_or_404(HealthFacilityBase, pk=facility_pk)
    if request.method == 'POST':
        facility.delete()
    return HttpResponse(status=200)

@login_required
def editFacility(request, facility_pk):
    facility = get_object_or_404(HealthFacilityBase, pk=facility_pk)
    facility_form = FacilityForm(instance=facility, username=request.user)
    if request.method == 'POST':
        facility_form = FacilityForm(instance=facility,
                data=request.POST)
        if facility_form.is_valid():
            facility_form.save()
            return generic_row(request, model=Facilities, pk=facility_pk, partial_row='/cvs/facility/partials/facility_row.html')
        else:
            return render_to_response('cvs/facility/partials/edit_facility.html'
                    , {'facility_form': facility_form, 'facility'
                    : facility},
                    context_instance=RequestContext(request))
    else:
        return render_to_response('cvs/facility/partials/edit_facility.html',
                                  {'facility_form': facility_form,
                                  'facility': facility},
                                  context_instance=RequestContext(request))


def editFacilityLocations(request, facility_pk=None, district_pk=None):
    if facility_pk:
        facility = get_object_or_404(HealthFacilityBase, pk=facility_pk)
        areas = facility.catchment_areas.all()
    else: areas = None
    if district_pk:
        district = get_object_or_404(Location, pk=district_pk)
    else:
        district = get_district_for_facility(facility)
    locations = district.get_descendants(include_self=True)
    return render_to_response(
      'cvs/facility/partials/edit_facility_locations.html',
      {
          'catchment_areas':areas,
          'locations':locations
      },
      context_instance=RequestContext(request))

@transaction.commit_manually
def newFacility(request):
    if request.method == 'POST':
        facility_form = FacilityForm(data=request.POST, username=request.user)
        if facility_form.is_valid():
            # facility_form.facility = HealthFacility.objects.create()
            # facility_form.save()
            facility_form.facility = HealthFacility.objects.create(name=facility_form.cleaned_data['name'],
                                          code=facility_form.cleaned_data['code'],
                                          type=facility_form.cleaned_data['type'])
            transaction.commit()
            facility_form.save()
            facility = facility_form.facility
            transaction.commit()
            return render_to_response('cvs/facility/partials/new_facility.html',
                                      {'facility_form':facility_form,
                                       'added_facility':facility},
                                      context_instance=RequestContext(request))
        else:
            toret = render_to_response('cvs/facility/partials/new_facility.html',
                                      {'facility_form':facility_form},
                                      context_instance=RequestContext(request))
            transaction.commit()
            return toret
    else:
        facility_form = FacilityForm(username=request.user)
        toret = render_to_response('cvs/facility/partials/new_facility.html',
                                  {'facility_form':facility_form},
                                  context_instance=RequestContext(request))
        transaction.commit()
        return toret

def facilityDetails(request, facility_pk=0):
    facility = HealthFacilityBase.objects.select_related('type__name', 'catchment_areas', '').get(pk=facility_pk)
    if request.method == "GET":
        return render_to_response("cvs/facility/partials/facility_detail_row.html",
                                  {'object':facility},
                                  context_instance=RequestContext(request)
                                  )

def facilityReportCompleteness(request, facility_pk=0):
    required_keywords = getattr(settings, 'COMPLETE_REPORTS_KEYWORDS',
                                ['act', 'cases', 'death', 'treat', 'test', 'opd', 'rdt', 'qun'])
    reports = XFormSubmissionExtras.objects.filter(facility=facility_pk,
            submission__has_errors=False,
            submission__xform__keyword__in=required_keywords,
            cdate__range=last_reporting_period(period=0, todate=True))
    reporters = reports.values('submission__connection', 'reporter__name',
                               'submission__connection__identity').distinct()

    reports = reports.distinct().\
    values_list('submission__message__text', flat=True)
    print reporters
    if request.method == "GET":
        return render_to_response("cvs/facility/partials/facility_completeness_row.html",
                                  {'reports': reports, 'reporters': reporters},
                                  context_instance=RequestContext(request)
                                  )

def sendSMS(request, facility_pk=0):
    groups = Group.objects.filter(name__in=['FHD', 'HC',
                                            'Incharge', 'Records Assistant', 'VHT']).order_by('name')
    facility = HealthFacility.objects.get(pk=facility_pk)
    if request.method == "GET":
        return render_to_response("cvs/facility/partials/facility_sendsms.html",
                                  {'groups': groups, 'facility': facility},
                                  context_instance=RequestContext(request)
                                  )
    else:
        msg = request.POST['msg']
        grp = request.POST['group']
        if not grp:
            json = simplejson.dumps({'error': "role is required"})
            return HttpResponse(json, mimetype='application/json')
        if not msg:
            json = simplejson.dumps({'error': "message is required"})
            return HttpResponse(json, mimetype='application/json')
        reporters = HealthProvider.objects.filter(facility=request.POST['facility'],
                                                  groups__in=[grp])
        recipient_count = reporters.count()
        conns = Connection.objects.filter(contact__in=reporters)
        Message.mass_text(msg, conns, status='Q', batch_status='Q')
        json = simplejson.dumps({'msg': "sent to %s recipients" % recipient_count, 'error': ""})
        return HttpResponse(json, mimetype='application/json')

def get_facility_reports(request, facility_pk=0):
    reports = XFormSubmissionExtras.objects.filter(facility=facility_pk).\
    exclude(submission__has_errors=True).order_by('-cdate')
    facility = reports[0].facility.name if reports else ''
    return generic(
                   request=request,
                   model=XFormSubmissionExtras,
                   queryset=reports,
                   objects_per_page=25,
                   partial_row='cvs/facility/partials/facility_report_row.html',
                   paginator_template='cvs/partials/new_pagination.html',
                   partial_header='cvs/facility/partials/facility_report_header.html',
                   base_template='cvs/facility/facility_base.html',
                   # columns=[('Text', 'Reporter', 'Date', '')],
                   results_title='%s Reports' % facility,
                   sort_column='cdate',
                   selectable=False,
                   paginator_func=mtrac_paginate,
                   sort_ascending=False
            )
