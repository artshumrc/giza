(function () {
  var INSTANCE_NAME = 'giza-search';
  var SEARCH_SCOPE_FILTER = 'search_scope';
  var SEARCH_SCOPE_VALUE = 'catalog';
  var DEFAULT_IMAGE = '/static/images/object1.png';
  var CATEGORY_LABELS = {
    photos: 'Photos',
    objects: 'Objects',
    unpubdocs: 'Unpublished Documents',
    mapsandplans: 'Maps and Plans',
    diarypages: 'Diary Pages',
    drawings: 'Drawings',
    sites: 'Tombs and Monuments',
    ancientpeople: 'Ancient People',
    videos: 'Videos',
    modernpeople: 'Modern People',
    pubdocs: 'Published Documents',
    institutions: 'Institutions',
    '3dmodels': '3D Models',
    groups: 'Groups',
    animals: 'Animals'
  };
  var CATEGORY_ORDER = [
    'Photos',
    'Objects',
    'Unpublished Documents',
    'Maps and Plans',
    'Diary Pages',
    'Drawings',
    'Tombs and Monuments',
    'Ancient People',
    'Videos',
    'Modern People',
    'Published Documents',
    'Institutions',
    '3D Models',
    'Groups',
    'Animals'
  ];
  var ADVANCED_FIELDS = [
    { name: 'objects_title', names: ['objects_title', 'title'], label: 'Object title or name', group: 'objects' },
    { name: 'objects_allnumbers', names: ['objects_allnumbers', 'allnumbers'], label: 'Object or ID number', group: 'objects' },
    { name: 'objects_medium', names: ['objects_medium', 'medium'], label: 'Material', group: 'objects' },
    { name: 'objects_provenance', names: ['objects_provenance', 'provenance'], label: 'Findspot', group: 'objects' },
    { name: 'objects_entrydate', names: ['objects_entrydate', 'entrydate'], label: 'Date of register entry', group: 'objects' },
    { name: 'sites_number', names: ['sites_number', 'number'], label: 'Tomb/Monument number', group: 'sites' },
    { name: 'sites_sitename', names: ['sites_sitename', 'sitename'], label: 'Tomb/Monument name', group: 'sites' },
    { name: 'sites_datevalues', names: ['sites_datevalues', 'datevalues'], label: 'Site Dates', group: 'sites' },
    { name: 'sites_people', names: ['sites_people', 'people'], label: 'People', group: 'sites' }
  ];
  var CATEGORY_LOOKUP = {};
  var CATEGORY_SLUGS_BY_LABEL = {};
  var SearchRuntime = {
    applyingUrlState: false,
    categoryCountsCache: {},
    categoryCountsPromises: {},
    enforcingCatalog: false,
    initStarted: false,
    instance: null,
    dredgeClientPromise: null,
    suppressNextPageReset: false,
    suppressNextUrlSync: false
  };

  Object.keys(CATEGORY_LABELS).forEach(function (slug) {
    var label = CATEGORY_LABELS[slug];
    CATEGORY_LOOKUP[normalizeCategoryKey(slug)] = label;
    CATEGORY_LOOKUP[normalizeCategoryKey(label)] = label;
    CATEGORY_SLUGS_BY_LABEL[label] = slug;
  });
  CATEGORY_LOOKUP.tombs = CATEGORY_LABELS.sites;
  CATEGORY_LOOKUP.tomb = CATEGORY_LABELS.sites;
  CATEGORY_LOOKUP.tombsandmonuments = CATEGORY_LABELS.sites;

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function escapeAttr(value) {
    return escapeHtml(value);
  }

  function normalizeCategoryKey(value) {
    return String(value || '')
      .trim()
      .toLowerCase()
      .replace(/&/g, 'and')
      .replace(/[^a-z0-9]+/g, '');
  }

  function categoryLabelFromParam(value) {
    return CATEGORY_LOOKUP[normalizeCategoryKey(value)] || '';
  }

  function categorySlugForLabel(label) {
    return CATEGORY_SLUGS_BY_LABEL[label] || '';
  }

  function firstFilledParam(params, names) {
    for (var i = 0; i < names.length; i += 1) {
      var value = params.get(names[i]);
      if (value && value.trim()) {
        return { name: names[i], value: value.trim() };
      }
    }
    return null;
  }

  function advancedRowsFromParams(params) {
    var rows = [];
    ADVANCED_FIELDS.forEach(function (field) {
      var match = firstFilledParam(params, field.names);
      if (match) {
        rows.push({
          key: field.name,
          group: field.group,
          label: field.label,
          value: match.value
        });
      }
    });
    return rows;
  }

  function inferCategoryFromRows(rows) {
    for (var i = 0; i < rows.length; i += 1) {
      if (rows[i].group === 'sites') return CATEGORY_LABELS.sites;
    }
    for (var j = 0; j < rows.length; j += 1) {
      if (rows[j].group === 'objects') return CATEGORY_LABELS.objects;
    }
    return '';
  }

  function stateFromParams(params) {
    var simple = firstFilledParam(params, ['q', 'query']);
    var rows = advancedRowsFromParams(params);
    var parts = [];
    if (simple) parts.push(simple.value);
    rows.forEach(function (row) {
      parts.push(row.value);
    });
    return {
      category: categoryLabelFromParam(params.get('category')) || inferCategoryFromRows(rows),
      rows: rows,
      simple: simple ? simple.value : '',
      sort: (params.get('sort') || '').toLowerCase(),
      term: parts.join(' ').trim()
    };
  }

  function currentParams() {
    return new URLSearchParams(window.location.search);
  }

  function parsePageParam() {
    var value = parseInt(currentParams().get('page') || '1', 10);
    return Number.isFinite(value) && value > 0 ? value : 1;
  }

  function isBrowseState(state) {
    return !state.term;
  }

  // Available result orderings. "relevance" (bm25) only makes sense when there
  // is a keyword query, so it is hidden/ignored for empty-query browse.
  var SORT_OPTIONS = [
    { value: 'relevance', label: 'Relevance' },
    { value: 'title', label: 'Title (A\u2013Z)' },
    { value: 'id', label: 'ID' }
  ];

  function defaultSortForTerm(hasTerm) {
    return hasTerm ? 'relevance' : 'title';
  }

  // Resolve the effective sort for a state: honour the URL `sort` param when
  // valid, otherwise fall back to the context default. "relevance" is demoted
  // to the default when there is no keyword query.
  function resolveSort(state) {
    var hasTerm = Boolean(state && state.term);
    var requested = String((state && state.sort) || '').toLowerCase();
    if (requested === 'relevance' && !hasTerm) {
      requested = '';
    }
    if (requested !== 'relevance' && requested !== 'title' && requested !== 'id') {
      return defaultSortForTerm(hasTerm);
    }
    return requested;
  }

  // Translate a resolved sort value into a Dredge sort directive. "relevance"
  // maps to no directive so the worker uses bm25 (keyword) ordering. "id" sorts
  // by the user-visible catalog identifier shown on each result card.
  function dredgeSortFor(sortValue) {
    if (sortValue === 'title') return { field: 'title', direction: 'asc' };
    if (sortValue === 'id') return { field: 'catalog_id', direction: 'asc' };
    return null;
  }

  function updateUrl(params, path, replace) {
    var query = params.toString();
    var nextPath = path || window.location.pathname || '/search-results/';
    var nextUrl = nextPath + (query ? '?' + query : '');
    if (nextUrl === window.location.pathname + window.location.search) return;
    if (replace) {
      window.history.replaceState(null, '', nextUrl);
    } else {
      window.history.pushState(null, '', nextUrl);
    }
    window.dispatchEvent(new CustomEvent('giza:search-url-change'));
  }

  function urlForParams(params, path) {
    var query = params.toString();
    return (path || window.location.pathname || '/search-results/') + (query ? '?' + query : '');
  }

  function updatePageParam(page, replace) {
    var params = currentParams();
    if (page > 1) {
      params.set('page', String(page));
    } else {
      params.delete('page');
    }
    updateUrl(params, null, replace);
  }

  function cloneFilterValue(value) {
    if (Array.isArray(value)) {
      return value.map(String).filter(Boolean);
    }
    if (value == null || value === '') {
      return [];
    }
    return [String(value)];
  }

  function scopeOnlyFilters() {
    var filters = {};
    filters[SEARCH_SCOPE_FILTER] = [SEARCH_SCOPE_VALUE];
    return filters;
  }

  function filtersForCategory(categoryLabel) {
    var filters = scopeOnlyFilters();
    if (categoryLabel) {
      filters.category = [categoryLabel];
    }
    return filters;
  }

  function categoryCountsFromSearchResult(searchResult) {
    if (searchResult && searchResult.totalFilters && searchResult.totalFilters.category) {
      return searchResult.totalFilters.category;
    }
    if (searchResult && searchResult.filters && searchResult.filters.category) {
      return searchResult.filters.category;
    }
    return {};
  }

  function hasSwitchableCategoryCounts(categoryCounts, activeCategory) {
    return CATEGORY_ORDER.some(function (label) {
      return label !== activeCategory && Number((categoryCounts || {})[label]) > 0;
    });
  }

  function shouldLoadCategoryCounts(categoryCounts, activeCategory) {
    if (!Object.keys(categoryCounts || {}).length) return true;
    return Boolean(activeCategory && !hasSwitchableCategoryCounts(categoryCounts, activeCategory));
  }

  function categoryCountsCacheKey(term) {
    return String(term || '').trim();
  }

  function cachedCategoryCountsForTerm(term) {
    var key = categoryCountsCacheKey(term);
    if (!key || !Object.prototype.hasOwnProperty.call(SearchRuntime.categoryCountsCache, key)) {
      return null;
    }
    return SearchRuntime.categoryCountsCache[key];
  }

  function cacheCategoryCountsForTerm(term, categoryCounts) {
    var key = categoryCountsCacheKey(term);
    if (!key) return categoryCounts || {};
    SearchRuntime.categoryCountsCache[key] = categoryCounts || {};
    return SearchRuntime.categoryCountsCache[key];
  }

  function activeCategoryFromFilters(filters) {
    return cloneFilterValue(filters && filters.category)[0] || '';
  }

  function filterSignature(filters) {
    var normalized = {};
    Object.keys(filters || {}).sort().forEach(function (key) {
      normalized[key] = cloneFilterValue(filters[key]).sort();
    });
    return JSON.stringify(normalized);
  }

  function searchSignature(term, filters, sort) {
    return String(term || '') + '|' + filterSignature(filters || {}) + '|' + String(sort || '');
  }

  async function loadDredge() {
    if (SearchRuntime.dredgeClientPromise) return SearchRuntime.dredgeClientPromise;
    SearchRuntime.dredgeClientPromise = import('/search/dredge-client.js').then(function (module) {
      var client = new module.DredgeSearchClient();
      return client.init().then(function () { return client; });
    }).catch(function (error) {
      SearchRuntime.dredgeClientPromise = null;
      throw error;
    });
    return SearchRuntime.dredgeClientPromise;
  }

  // Translate giza's filter shape into Dredge filters. The redundant
  // search_scope filter is dropped: the Dredge index only contains catalog
  // item pages (scoped by the build's include glob), so it is implicit.
  function dredgeFiltersFor(filters) {
    var out = {};
    var categories = cloneFilterValue(filters && filters.category);
    if (categories.length) out.category = categories;
    return out;
  }

  // Build a {label: count} map from a Dredge category facet response. Dredge
  // computes each facet ignoring its own filter, so these counts stay
  // switchable even when a category is currently selected.
  function facetCountsFromResponse(response) {
    var counts = {};
    var buckets = response && response.facets && response.facets.category;
    if (Array.isArray(buckets)) {
      buckets.forEach(function (bucket) {
        if (bucket && bucket.value != null) {
          counts[String(bucket.value)] = Number(bucket.count) || 0;
        }
      });
    }
    return counts;
  }

  // Fetch a single page of results plus the total and category facet counts.
  // Pagination is performed server-side in the worker via LIMIT/OFFSET. The
  // resolved sort controls ordering; an empty query defaults to title order.
  async function dredgeSearchPage(term, filters, page, pageSize, sortValue) {
    var searchTerm = String(term || '').trim();
    var client = await loadDredge();
    var currentPage = Math.max(1, Number(page) || 1);
    var request = {
      query: searchTerm,
      filters: dredgeFiltersFor(filters),
      limit: pageSize,
      offset: (currentPage - 1) * pageSize,
      includeFacets: ['category']
    };
    var sort = dredgeSortFor(sortValue);
    if (sort) {
      request.sort = sort;
    }
    return client.search(request);
  }

  function selectedRowsForSidebar(instance) {
    var params = currentParams();
    var state = stateFromParams(params);
    var rows = [];
    if (state.simple) {
      rows.push({ label: 'Keyword', value: state.simple });
    }
    state.rows.forEach(function (row) {
      rows.push({ label: row.label, value: row.value });
    });
    if (!rows.length && !isBrowseState(state) && instance && instance.searchTerm) {
      rows.push({ label: 'Keyword', value: instance.searchTerm });
    }
    return rows;
  }

  function applyCategory(instance, categoryLabel) {
    var params = currentParams();
    params.delete('page');
    if (categoryLabel) {
      params.set('category', categorySlugForLabel(categoryLabel) || categoryLabel);
    } else {
      params.delete('category');
    }
    updateUrl(params, null, false);
  }

  function applySort(sortValue) {
    var params = currentParams();
    params.delete('page');
    var hasTerm = Boolean(stateFromParams(params).term);
    if (sortValue && sortValue !== defaultSortForTerm(hasTerm)) {
      params.set('sort', sortValue);
    } else {
      params.delete('sort');
    }
    updateUrl(params, null, false);
  }

  // Render the result-ordering control. "Relevance" is omitted when there is no
  // keyword query, since match-all browse has no relevance score.
  function renderSortControl(activeSort, hasTerm) {
    var options = SORT_OPTIONS.filter(function (option) {
      return option.value !== 'relevance' || hasTerm;
    }).map(function (option) {
      var selected = option.value === activeSort ? ' selected' : '';
      return '<option value="' + option.value + '"' + selected + '>' + escapeHtml(option.label) + '</option>';
    }).join('');
    return [
      '<label class="static-site-sort">',
      '<span class="static-site-sort-label">Sort by</span>',
      '<select class="static-site-sort-select" data-search-sort aria-label="Sort results by">',
      options,
      '</select>',
      '</label>'
    ].join('');
  }

  function setupAdvancedForm() {
    var form = document.getElementById('advanced-search-form');
    if (!form) return;

    function setFormFromUrl() {
      var params = currentParams();
      var rows = advancedRowsFromParams(params);
      var category = categoryLabelFromParam(params.get('category')) || inferCategoryFromRows(rows) || CATEGORY_LABELS.objects;
      var slug = categorySlugForLabel(category);
      ADVANCED_FIELDS.forEach(function (field) {
        var input = form.elements[field.name];
        var match = firstFilledParam(params, field.names);
        if (input) input.value = match ? match.value : '';
      });
      Array.prototype.forEach.call(form.querySelectorAll('input[name="category"]'), function (radio) {
        radio.checked = Boolean(slug && radio.value === slug);
      });
      if (!slug) {
        var defaultRadio = form.querySelector('input[name="category"][value="objects"]');
        if (defaultRadio) defaultRadio.checked = true;
      }
      updateAdvancedSections();
    }

    function updateAdvancedSections() {
      var checked = form.querySelector('input[name="category"]:checked');
      var targetId = checked ? checked.getAttribute('data-for-id') : 'section-objects';
      Array.prototype.forEach.call(form.querySelectorAll('.category-section'), function (section) {
        section.style.display = section.id === targetId ? '' : 'none';
      });
    }

    setFormFromUrl();
    form.addEventListener('change', function (event) {
      if (event.target && event.target.name === 'category') {
        updateAdvancedSections();
      }
    });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var params = new URLSearchParams();
      Array.prototype.forEach.call(form.elements, function (field) {
        if (!field.name || field.disabled) return;
        if ((field.type === 'radio' || field.type === 'checkbox') && !field.checked) return;
        var value = String(field.value || '').trim();
        if (value) params.set(field.name, value);
      });
      params.delete('page');
      var action = form.getAttribute('action') || '/search-results/';
      if (!document.querySelector('giza-search-results')) {
        window.location.href = urlForParams(params, action);
        return;
      }
      updateUrl(params, action, false);
    });
    window.addEventListener('popstate', setFormFromUrl);
    window.addEventListener('giza:search-url-change', setFormFromUrl);
  }

  function renderPagination(currentPage, totalPages) {
    if (totalPages <= 1) return '';
    var items = [];
    var previousClass = currentPage <= 1 ? ' class="pagination-previous disabled"' : ' class="pagination-previous"';
    var nextClass = currentPage >= totalPages ? ' class="pagination-next disabled"' : ' class="pagination-next"';
    items.push('<li' + previousClass + '>' + (currentPage <= 1 ? 'Previous' : '<a href="#" data-search-page="' + (currentPage - 1) + '" aria-label="Previous page">Previous</a>') + '</li>');

    var lastWasEllipsis = false;
    for (var page = 1; page <= totalPages; page += 1) {
      var visible = page === 1 || page === totalPages || Math.abs(page - currentPage) <= 2;
      if (!visible) {
        if (!lastWasEllipsis) {
          items.push('<li class="ellipsis"></li>');
          lastWasEllipsis = true;
        }
        continue;
      }
      lastWasEllipsis = false;
      if (page === currentPage) {
        items.push('<li class="current"><span class="show-for-sr">You are on page</span> ' + page + '</li>');
      } else {
        items.push('<li><a href="#" data-search-page="' + page + '" aria-label="Page ' + page + '">' + page + '</a></li>');
      }
    }
    items.push('<li' + nextClass + '>' + (currentPage >= totalPages ? 'Next' : '<a href="#" data-search-page="' + (currentPage + 1) + '" aria-label="Next page">Next</a>') + '</li>');
    return '<div class="row"><div class="text-center columns p-t-1"><nav aria-label="Pagination"><ul class="pagination m-l-neghalf">' + items.join('') + '</ul></nav></div></div>';
  }

  function renderResultCard(data) {
    var meta = data.meta || {};
    var url = meta.url || data.url || '#';
    var title = meta.title || data.title || url;
    var catalogId = meta.catalog_id || data.catalog_id || '';
    var thumbnail = meta.thumbnail || data.thumbnail || '';
    var image = thumbnail || meta.image || data.image || DEFAULT_IMAGE;
    var thumbClass = thumbnail ? 'thumbnail' : 'thumbnail no-img';
    var subheader = [];
    if (catalogId) subheader.push('<li>' + escapeHtml(catalogId) + '</li>');
    return [
      '<div class="media-object list-item search-result thumbsize-md thumbs-square">',
      '<div class="media-object-section"><div class="' + thumbClass + '"><a href="' + escapeAttr(url) + '"><img src="' + escapeAttr(image) + '" alt=""></a></div></div>',
      '<div class="media-object-section"><p class="media-object-title"><a href="' + escapeAttr(url) + '">' + escapeHtml(title) + '</a></p>',
      '<ul class="subheader">' + subheader.join('') + '</ul></div>',
      '</div>'
    ].join('');
  }

  function defineSearchComponents() {
    if (!window.customElements || customElements.get('giza-search-results')) return;

    class GizaSearchSidebar extends HTMLElement {
      connectedCallback() {
        this.instanceName = this.getAttribute('instance') || INSTANCE_NAME;
        this.categoryCounts = {};
        this.activeCategory = categoryLabelFromParam(currentParams().get('category'));
        this.loadingCategories = true;
        this.render();
        this._handleSearchStart = (event) => {
          this.loadingCategories = true;
          this.render();
        };
        this._handleDirectSearchResults = (event) => {
          var detail = event.detail || {};
          var searchResult = detail.searchResult || {};
          var hasCategoryCounts = Object.prototype.hasOwnProperty.call(detail, 'category_counts');
          if (hasCategoryCounts) {
            this.categoryCounts = detail.category_counts || {};
          } else {
            this.categoryCounts = categoryCountsFromSearchResult(searchResult);
          }
          this.activeCategory = activeCategoryFromFilters(detail.filters || {});
          this.loadingCategories = detail.is_final_counts !== undefined ? !detail.is_final_counts : shouldLoadCategoryCounts(this.categoryCounts, this.activeCategory);
          this.render();
        };
        window.addEventListener('giza:search-start', this._handleSearchStart);
        window.addEventListener('giza:direct-search-results', this._handleDirectSearchResults);
        this.addEventListener('click', (event) => {
          var link = event.target.closest('[data-search-category]');
          if (!link) return;
          event.preventDefault();
          var label = link.getAttribute('data-search-category') || '';
          applyCategory(this.instance, label === this.activeCategory ? '' : label);
        });
      }

      disconnectedCallback() {
        if (this._handleSearchStart) {
          window.removeEventListener('giza:search-start', this._handleSearchStart);
        }
        if (this._handleDirectSearchResults) {
          window.removeEventListener('giza:direct-search-results', this._handleDirectSearchResults);
        }
      }

      render() {
        var rows = selectedRowsForSidebar(this.instance);
        var counts = this.categoryCounts || {};
        var hasCounts = Object.keys(counts).length > 0;
        var html = ['<div class="feature-block secondary text-smaller"><h5 class="heading-alt">Search Options</h5><p><a href="/search/">Start a new search</a></p>'];
        if (rows.length) {
          html.push('<div class="search-facet-section">');
          rows.forEach(function (row) {
            html.push('<h6 class="search-facet-title">' + escapeHtml(row.label) + ':</h6><ul class="search-facet-list"><li class="is-active">' + escapeHtml(row.value) + '</li></ul>');
          });
          html.push('</div>');
        }
        if (this.loadingCategories) {
          html.push('<div class="search-facet-section"><h6 class="search-facet-title">Category:</h6> ');
          html.push('<div class="category-loading"><div class="giza-spinner spinner-sm"></div><p class="static-site-meta">Loading categories...</p></div>');
          html.push('</div>');
        } else if (hasCounts || this.activeCategory) {
          html.push('<div class="search-facet-section"><h6 class="search-facet-title">Category:</h6><ul class="search-facet-list">');
          CATEGORY_ORDER.slice().sort(function (a, b) {
            return (counts[b] || 0) - (counts[a] || 0) || CATEGORY_ORDER.indexOf(a) - CATEGORY_ORDER.indexOf(b);
          }).forEach((label) => {
            var count = counts[label] || 0;
            if (!count && label !== this.activeCategory) return;
            var active = label === this.activeCategory;
            var params = currentParams();
            params.delete('page');
            if (active) {
              params.delete('category');
            } else {
              params.set('category', categorySlugForLabel(label) || label);
            }
            var href = (window.location.pathname || '/search-results/') + (params.toString() ? '?' + params.toString() : '');
            html.push('<li class="search-facet-item' + (active ? ' is-active' : '') + '"><a href="' + escapeAttr(href) + '" data-search-category="' + escapeAttr(label) + '">' + escapeHtml(label) + ' (' + count + ')</a></li>');
          });
          html.push('</ul></div>');
        }
        html.push('</div>');
        this.innerHTML = html.join('');
      }
    }

    class GizaSearchResults extends HTMLElement {
      connectedCallback() {
        this.instanceName = this.getAttribute('instance') || INSTANCE_NAME;
        this.pageSize = parseInt(this.getAttribute('page-size') || '20', 10) || 20;
        this.currentPage = parsePageParam();
        this.renderToken = 0;
        this.signature = '';
        this.innerHTML = '<div class="static-site-loading"><div class="giza-spinner"></div><p class="static-site-meta">Loading search results...</p></div>';
        this.addEventListener('click', (event) => {
          var link = event.target.closest('[data-search-page]');
          if (!link) return;
          event.preventDefault();
          var page = parseInt(link.getAttribute('data-search-page') || '1', 10);
          if (!Number.isFinite(page) || page < 1) return;
          this.currentPage = page;
          updatePageParam(page, false);
          this.scrollIntoView({ block: 'start', behavior: 'smooth' });
        });
        this.addEventListener('change', (event) => {
          var select = event.target.closest('[data-search-sort]');
          if (!select) return;
          applySort(select.value);
        });
        var syncPageFromUrl = () => {
          this.currentPage = parsePageParam();
          this.runDirectSearchFromUrl().catch((error) => {
            this.innerHTML = '<p class="callout alert">Search failed: ' + escapeHtml(error && error.message ? error.message : error) + '</p>';
          });
        };
        window.addEventListener('popstate', syncPageFromUrl);
        window.addEventListener('giza:search-url-change', syncPageFromUrl);
        this.runDirectSearchFromUrl().catch(() => {
          this.innerHTML = '<p class="callout warning">Search is unavailable: the Dredge index could not be loaded for this static build.</p>';
        });
      }

      async runDirectSearchFromUrl() {
        var state = stateFromParams(currentParams());
        var browse = isBrowseState(state);
        var filters = filtersForCategory(state.category);
        var sortValue = resolveSort(state);
        var page = parsePageParam();
        this.currentPage = page;
        var token = ++this.renderToken;
        window.dispatchEvent(new CustomEvent('giza:search-start', { detail: { isBrowse: browse, state: state } }));
        this.innerHTML = '<div class="static-site-loading"><div class="giza-spinner"></div><p class="static-site-meta">' + (browse ? 'Loading search results...' : 'Searching...') + '</p></div>';
        var response;
        try {
          response = await dredgeSearchPage(state.term, filters, page, this.pageSize, sortValue);
        } catch (error) {
          if (error && error.code === 'STALE_RESPONSE') return;
          throw error;
        }
        if (token !== this.renderToken) return;
        var latestState = stateFromParams(currentParams());
        var latestFilters = filtersForCategory(latestState.category);
        var latestSort = resolveSort(latestState);
        if (searchSignature(state.term, filters, sortValue) !== searchSignature(latestState.term, latestFilters, latestSort) || parsePageParam() !== page) {
          return;
        }
        var categoryCounts = facetCountsFromResponse(response);
        this.lastResponse = response;
        window.dispatchEvent(new CustomEvent('giza:direct-search-results', {
          detail: {
            searchResult: null,
            filters: filters,
            category_counts: categoryCounts,
            is_final_counts: true
          }
        }));
        this.renderDredgeResults(response, page);
      }

      renderDredgeResults(response, page) {
        var total = Number(response && response.total) || 0;
        var totalPages = Math.max(1, Math.ceil(total / this.pageSize));
        if (page > totalPages && total > 0) {
          this.currentPage = totalPages;
          updatePageParam(totalPages, true);
          return;
        }
        var state = stateFromParams(currentParams());
        var noun = total === 1 ? 'search result' : 'search results';
        var heading = '<h3 class="heading-alt m-t-half m-b-1">' + String(total) + ' ' + noun + ' found.</h3>';
        var sortControl = total ? renderSortControl(resolveSort(state), Boolean(state.term)) : '';
        var status = '<div class="static-site-search-status">' + heading + sortControl + '</div>';
        if (!total) {
          this.innerHTML = status + '<p>No catalog records matched this search.</p>';
          return;
        }
        var hits = (response && response.hits) || [];
        var cards = hits.map(function (hit) { return renderResultCard({ meta: hit }); }).join('');
        this.innerHTML = status + '<div class="media-object-holder">' + cards + '</div>' + renderPagination(page, totalPages);
      }
    }

    customElements.define('giza-search-sidebar', GizaSearchSidebar);
    customElements.define('giza-search-results', GizaSearchResults);
  }

  window.GizaStaticSite = window.GizaStaticSite || {};
  window.GizaStaticSite.initStaticSearch = function () {
    if (SearchRuntime.initStarted || !document.querySelector('[data-giza-search-page]')) return;
    SearchRuntime.initStarted = true;
    defineSearchComponents();
    setupAdvancedForm();
  };
}());
