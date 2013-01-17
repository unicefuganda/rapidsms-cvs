from django import template
from rapidsms.contrib.locations.models import Location

register = template.Library()

@register.filter
def district_id(district):
    return Location.objects.filter(type='district').get(name__iexact=district).pk