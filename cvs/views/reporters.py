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

@login_required
def editReporter(request, reporter_pk):
    reporter = get_object_or_404(HealthProviderBase, pk=reporter_pk)
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
        return render_to_response('/cvs/partials/reporter_row.html',
                                  {'object':HealthProviderBase.objects.get(pk=reporter_pk)},
                                  context_instance=RequestContext(request))
    else:
        return render_to_response('cvs/partials/edit_reporter.html',
                                  {'reporter_form': reporter_form,
                                  'reporter': reporter},
                                  context_instance=RequestContext(request))
