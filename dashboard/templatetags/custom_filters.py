from django import template

register = template.Library()

@register.filter
def filter_status(value, status):
    """Filter a list of namespaces by their status"""
    if not value:
        return []
    return [ns for ns in value if ns.get('status', '').lower() == status.lower()]

@register.filter
def sub(value, arg):
    """Subtract the arg from the value"""
    try:
        # Convert both values to integers
        value = int(value)
        arg = int(arg) if isinstance(arg, (int, str)) else len(arg)
        return value - arg
    except (TypeError, ValueError):
        return 0

@register.filter
def map(value, key):
    """Extract values from a list of dictionaries using the specified key"""
    if not value:
        return []
    try:
        return [item.get(key) for item in value if key in item]
    except (AttributeError, TypeError):
        return []

@register.filter(name='max_value')
def max_value(value):
    """Find the maximum value in a list"""
    if not value:
        return None
    try:
        # Convert all values to integers if possible
        values = [int(v) if str(v).isdigit() else v for v in value if v is not None]
        return max(values) if values else None
    except (TypeError, ValueError):
        return None

@register.filter(name='min_value')
def min_value(value):
    """Find the minimum value in a list"""
    if not value:
        return None
    try:
        # Convert all values to integers if possible
        values = [int(v) if str(v).isdigit() else v for v in value if v is not None]
        return min(values) if values else None
    except (TypeError, ValueError):
        return None

@register.filter
def filter(value, condition):
    """Filter a list based on a condition"""
    if not value:
        return []
    try:
        key, val = condition.split('=')
        return [item for item in value if str(item.get(key, '')) == val]
    except (ValueError, AttributeError):
        return []

@register.filter
def length(value):
    """Get the length of a value"""
    try:
        return len(value)
    except (TypeError, AttributeError):
        return 0 