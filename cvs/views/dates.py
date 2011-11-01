from uganda_common.forms import DateRangeForm
from uganda_common.reports import XFormDateGetter
from django.db import connection
import datetime
from healthmodels.models import HealthProvider
from django.contrib.auth.models import Group
from math import floor

def get_expected_epi(location, request):
    dates = XFormDateGetter().get_dates(request)
    health_providers = HealthProvider.objects.filter(location__in=location.get_descendants(),
                                                     groups=Group.objects.get(name='VHT')).count()

    datediff = dates['end'] - dates['start']
    weeks = floor((datediff.days / 7))
    if weeks == 0:
        weeks = 1
    return health_providers * weeks

