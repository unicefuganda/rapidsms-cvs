#!/usr/bin/python
# -*- coding: utf-8 -*-
from django.template import RequestContext
from django.shortcuts import (render_to_response,get_object_or_404)
from django.http import HttpResponseRedirect
from healthmodels.models.HealthProvider import HealthProvider, \
    HealthProviderBase
from cvs.forms import EditReporterForm
from django.contrib.auth.decorators import login_required


@login_required
def deleteReporter(request, reporter_pk):
    reporter = get_object_or_404(HealthProviderBase, pk=reporter_pk)
    if request.method == 'POST':
        reporter.delete()


def editReporter(request, reporter_pk):
    reporter = get_object_or_404(HealthProviderBase, pk=reporter_pk)
    try:
        location_name = reporter.location.name
    except AttributeError:
        location_name = ''
    reporter_form = EditReporterForm(instance=reporter)
    if request.method == 'POST':
        reporter_form = EditReporterForm(instance=reporter,
                data=request.POST)
        if reporter_form.is_valid():
            reporter_form.save()
        else:
            return render_to_response('cvs/partials/edit_reporter.html'
                    , {'reporter_form': reporter_form, 'reporter'
                    : reporter},
                    context_instance=RequestContext(request))
        return HttpResponseRedirect('/cvs/reporter/%s/show/'
                                    % reporter_pk)
    else:
        return render_to_response('cvs/partials/edit_reporter.html',
                                  {'reporter_form': reporter_form,
                                  'reporter': reporter},
                                  context_instance=RequestContext(request))


def showReporter(request, reporter_pk):
    reporter = get_object_or_404(HealthProvider, pk=reporter_pk)
    return render_to_response('cvs/partials/show_reporter.html',
                              {'reporter': reporter},
                              context_instance=RequestContext(request))


