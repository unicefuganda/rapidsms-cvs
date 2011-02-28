from django import template

def dict(input, property):
    if property in input:
        return input[property]
    else:
        return None

def items_sorted(input):
    return [(key, input[key],) for key in input.keys()]

register = template.Library()
register.filter('dict', dict)
register.filter('items_sorted', items_sorted)
