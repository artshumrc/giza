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

@register.simple_tag
def build_search_params(search_params, current_category, current_subfacets, sf_to_remove, sf_to_add, page):
    url = ""
    url = "&amp;".join(["%s=%s" % (x[0], x[2]) for x in search_params])

    # add any chosen categories, unless we have one to remove
    if current_category:
        url = url + "&amp;category=%s" % current_category

    # sf_to_add and sf_to_remove are in the format [category]_[key]_[facet]
    # split them out for below
    sf_add_parts = sf_to_add.split('_')
    sf_remove_parts = sf_to_remove.split('_')

    # add any chosen subfacets, unless we have one to remove
    if current_category and current_category in current_subfacets:
        param = "&amp;%s_facet=" % current_category
        for k, facet_values in list(current_subfacets[current_category].items()):
            for v in facet_values:
                if len(sf_remove_parts) == 3 and sf_remove_parts[0] == current_category and sf_remove_parts[1] == k and sf_remove_parts[2] == v:
                    pass
                else:
                    url = url + param + "%s_%s" % (k, v)

    # add a new subfacet to url, if needed
    if len(sf_add_parts) == 3:
        url = url + "&amp;%s_facet=%s_%s" % (sf_add_parts[0], sf_add_parts[1], sf_add_parts[2])

    # add page
    if page:
        url = url + "&amp;page=%s" % page

    return url
