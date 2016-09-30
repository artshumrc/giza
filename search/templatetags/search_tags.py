from django import template
register = template.Library()

@register.filter
def keyvalue(dict, key):
    return dict[key]

@register.filter
def array_value(array, key):
    for a in array:
        if a['key'] == key:
            return a
