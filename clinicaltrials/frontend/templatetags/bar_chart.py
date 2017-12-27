import django
import math

register = django.template.Library()

def calc_bar(value, *args):
    """Calculate percentage of value out of the maximum
    of several values, for making a bar chart."""

    top = max(args + (value,))
    percent = value / top * 100
    return percent

def calc_mid_bar(value1, value2, *args):
    """Calculate percentage of value out of the maximum
    of several values, for making a bar chart. Return
    the midpoint between the height of the first and second
    parameter."""

    top = max(args + (value1, value2))
    percent = (value1 + value2) / 2 / top * 100
    return percent


register.simple_tag(calc_bar)
register.simple_tag(calc_mid_bar)
