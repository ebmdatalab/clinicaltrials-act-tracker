import django
import math

register = django.template.Library()

def default_if_nan(value, default):
    """Converts numbers which are NaN (not a number) to string"""
    if math.isnan(value):
        return default
    return value

def default_if_invalid(value, default):
    """Converts numbers which are None or NaN (not a number) to string"""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    return value

def custom_percent(value):
    """Display a number with a percent after it, or a dash if not valid"""
    if math.isnan(value):
        return "-"
    return str(value) + "%"

register.filter('default_if_nan', default_if_nan)
register.filter('default_if_invalid', default_if_invalid)
register.filter('custom_percent', custom_percent)
