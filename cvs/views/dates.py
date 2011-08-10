from cvs.forms import DateRangeForm
from django.db import connection
import datetime
from healthmodels.models import HealthProvider
from django.contrib.auth.models import Group
from math import floor

def get_expected_epi(location, request):
    dates = get_dates(request)
    health_providers = HealthProvider.objects.filter(location__in=location.get_descendants(),
                                                     groups=Group.objects.get(name='Village Health Team')).count()

    datediff = dates['end'] - dates['start']
    weeks = floor((datediff.days / 7))
    if weeks == 0:
        weeks = 1
    return health_providers * weeks

def get_dates(request):
    """
    Process date variables from POST
    """
    if request.POST:
        form = DateRangeForm(request.POST)
        if form.is_valid():
            cursor = connection.cursor()
            cursor.execute("select min(created) from rapidsms_xforms_xformsubmission")
            min_date = cursor.fetchone()[0] or (datetime.datetime.now() - datetime.timedelta(365))
            start_date = form.cleaned_data['start_ts']
            end_date = form.cleaned_data['end_ts']
            request.session['start_date'] = start_date
            request.session['end_date'] = end_date
    elif request.GET.get('start_date', None) and request.GET.get('end_date', None):
        start_date = datetime.datetime.fromtimestamp(int(request.GET['start_date']))
        end_date = datetime.datetime.fromtimestamp(int(request.GET['end_date']))
        request.session['start_date'] = start_date
        request.session['end_date'] = end_date
        return {'start':start_date, 'end':end_date}
    else:
        form = DateRangeForm()
        cursor = connection.cursor()
        cursor.execute("select min(created), max(created) from rapidsms_xforms_xformsubmission")
        min_date, end_date = cursor.fetchone()
        end_date = end_date or datetime.datetime.now()
        min_date = min_date or (datetime.datetime.now() - datetime.timedelta(365))
        start_date = end_date - datetime.timedelta(days=30)
        if request.GET.get('date_range', None):
            start_date, end_date = TIME_RANGES[request.GET.get('date_range')]()
            request.session['start_date'], request.session['end_date'] = start_date, end_date
        if request.session.get('start_date', None)  and request.session.get('end_date', None):
            start_date = request.session['start_date']
            end_date = request.session['end_date']

    return {'start':start_date, 'end':end_date, 'min':min_date, 'form':form}
