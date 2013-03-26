#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.template import RequestContext
from django.shortcuts import (render_to_response, get_object_or_404)
from django.http import HttpResponse
from healthmodels.models.HealthFacility import HealthFacility, \
    HealthFacilityBase, HealthFacilityType
from cvs.forms import FacilityForm
from django.contrib.auth.decorators import login_required
from generic.views import generic_row
from rapidsms.contrib.locations.models import Location
from mtrack.utils import get_district_for_facility
from mtrack.models import Facilities
# from cvs.views.facilities import facility_form
from django.views.decorators.cache import cache_page
from django.db import transaction

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

