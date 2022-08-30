from django import template
import re
register = template.Library()

from utils.views_utils import CATEGORIES

@register.filter
def keyvalue(dict, key):
    return dict[key]

@register.filter
def get_type(value):
    return value.__class__.__name__

@register.filter
def add_space(value):
    idx = [idx for idx in range(len(value)) if value[idx].isupper()]
    if len(idx) and '3D' not in value:
        for id in reversed(idx):
            if id != 0:
                value = value[:id] + ' ' + value[id:]
        return value
    elif '3D' in value:
        return '3D Models'
    else:
        return value

@register.filter
def array_value(array, key):
    # if key in array: return key
    for a in array:
        if a['key'] == key:
            return a

@register.filter
def lookup(array):
    l = { k : v for k, v in array.items() if type(v) is dict }
    return l
    
@register.filter
def sanitize(l):
    return [x for x in list(l) if '_ms' not in x[0]]

@register.filter
def next(l, current_index):
    """
    Returns the next element of the list using the current index if it exists.
    Otherwise returns an empty string.
    """
    try:
        return any([x for x in l if x.startswith(current_index)])
    except:
        return False # return empty string in case of exception

@register.filter
def previous(l, current_index):
    """
    Returns the previous element of the list using the current index if it exists.
    Otherwise returns an empty string.
    """
    try:
        return l[int(current_index) - 1]['code'] # access the previous element
    except:
        return False # return empty string in case of exception

@register.filter
def ending(value, total):
    """
    This filter returns a simple string with singular ending (-s) if any.
    """
    category = CATEGORIES[value]
    if total == 1:
        category = " ".join([x.lower() if not x.endswith('s') else x[:-1] for x in category.split(' ')])
    return category['key'].lower()