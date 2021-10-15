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

# THIS METHOD IS CALLED N-TIMES (N=NUMBER OF FACETS IN THE VIEW) EVERY TIME A FACET IS SELECTEd/DESELECTED
# THE METHOD DETERMINES IF FACETS NEED TO BE IN/EXCLUDED BASED ON THE CURRENT_SUBFACETS
# RECEIVES UPDATES THE FACETS ON THE SEARCHRESULTS.HTML PAGE BASED ON USER SELECTION OF FACETS
# THE URL IS BEING BUILT BASED ON THE SUBFACETS TO REMOVE/ADD
# INPUT:
#   - SEARCH_PARAMS
#   - CURRENT_CATEGORY
#   - CURRENT_SUBFACETS
#   - SF_TO_REMOVE
#   - SF_TO_ADD
#   - PAGE
# OUTPUT: URL TO NEW PAGE WITH UPDATED SEARCH PARAMETERS ADDED
@register.simple_tag
def build_search_params(search_params, current_category, current_subfacets, sf_to_remove, sf_to_add, page):

    # CONSTRUCT URL FROM CURRENT SEARCH PARAMETERS
    url = f'category={current_category}{"&amp;" if len(search_params) > 0 else ""}' if current_category else ""
    url += "&amp;".join([f'{x[0]}={x[2]}' for x in search_params])

    if current_category not in sf_to_remove:
        sf_to_remove = f'{current_category}{sf_to_remove}'

    # SPLIT sf_to_add AND sf_to_remove IN LISTS ([category]_[key]_[facet])
    sf_add_parts, sf_remove_parts = sf_to_add.split('_'), sf_to_remove.split('_')

    # ADD/REMOVE SELECTED SUBFACETS
    if current_category and current_category in current_subfacets:
        param = f'&amp;{current_category}_facet'
        for k, facet_values in list(current_subfacets[current_category].items()):
            for v in facet_values:
                if len(sf_remove_parts) == 3 and sf_remove_parts[0] == current_category and sf_remove_parts[1] == k and sf_remove_parts[2] == v:
                    pass
                else:
                    url = f'{url}{param}{k}_{v}'

    # ADD NEW SUBFACETS TO URL
    if len(sf_add_parts) == 3:
        url = f'{url}&amp;{sf_add_parts[0]}_facet={sf_add_parts[1]}_{sf_add_parts[2]}'

    # ADD PAGE ENDS
    if page:
        url = f'{url}&amp;page={page}'

    return url