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
def build_search_params(search_term, current_categories, cat_to_remove, cat_to_add, current_subfacets, sf_to_remove, sf_to_add, page):
    # always add search term
    url = "q=%s" % search_term

    # add any chosen categories, unless we have one to remove
    for c in current_categories:
        if c != cat_to_remove:
            url = url + "&amp;category=%s" % c

    # add a new category to url, if needed
    if cat_to_add:
        url = url + "&amp;category=%s" % cat_to_add

    # sf_to_add and sf_to_remove are in the format [category]_[key]_[facet]
    # split them out for below
    sf_add_parts = sf_to_add.split('_')
    sf_remove_parts = sf_to_remove.split('_')

    # add any chosen subfacets, unless we have one to remove
    # if cat_to_remove is in current_subfacets, remove all of those subfacets
    for category, subfacets in current_subfacets.items():
        if cat_to_remove == category:
            continue
        param = "&amp;%s_facet=" % category
        for k, v in subfacets.items():
            if len(sf_remove_parts) == 3 and sf_remove_parts[0] == category and sf_remove_parts[1] == k and sf_remove_parts[2] == v:
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
