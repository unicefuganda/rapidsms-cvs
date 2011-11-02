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

@login_required
def deleteFacility(request, facility_pk):
    facility = get_object_or_404(HealthFacilityBase, pk=facility_pk)
    if request.method == 'POST':
        facility.delete()
    return HttpResponse(status=200)

@login_required
def editFacility(request, facility_pk):
    facility = get_object_or_404(HealthFacilityBase, pk=facility_pk)
    facility_form = FacilityForm(instance=facility)
    if request.method == 'POST':
        facility_form = FacilityForm(instance=facility,
                data=request.POST)
        if facility_form.is_valid():
            facility_form.save()
            return generic_row(request, model=HealthFacilityBase, pk=facility_pk, partial_row='/cvs/facility/partials/facility_row.html')
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


def editFacilityLocations(request, facility_pk, district_pk):
    facility = get_object_or_404(HealthFacilityBase, pk=facility_pk)
    areas = facility.catchment_areas.all()
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


