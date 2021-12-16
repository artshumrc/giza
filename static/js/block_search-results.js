$(document).foundation()

$(document).ready(() => {

  st = JSON.parse($(search).text())

  // This method adds parameters to hidden fields in the post form to hide them in the URL
  $('input.advanced_search_field').on('change', e => addHidden($(e.currentTarget)))

  $('#advanced-search-form-btn')
  .on('click', e => {
    $('.advanced_search_field').removeAttr('name')
    $('#advanced-search-form').submit()
  })

  MET_list = []

  /*
  * This method is called when a facet's checkbox is toggled. The method first checks if a facet is selected/deselected
  * and updates the global items object accordingly. It then calls the post method (see update_search).
  * @param {string} facet The facet to evaluate for adding/removing
  */
  toggle_facet = facet => {

    // RESET THE PAGE FOR VIEWING
    st['result']['pages']['page'] = 1

    // CHECK IF FACET IS BEING ADDED OR REMOVED
    facet = facet.split('_')
    idx = st['facets'][facet[0]].map(e => e.display_text).indexOf(String(facet[1]))
    st['facets'][facet[0]][idx]['selected'] = !st['facets'][facet[0]][idx]['selected']

    // SEND AJAX POST REQUEST
    update_search()
  }

  /*
  * This method is called when a category is clicked and updates the global items object accordingly.
  * It then calls the post method (see update_search).
  */
  toggle_category = category => {

    // RESET THE CURRENT PAGE
    st['result']['pages']['page'] = 1

    // RESET THE DATE SLIDER
    delete st['fields']['entrydates_ms']
    
    // SET NEW CATEGORY STATE
    st['category'] = category.split('_')[1]
    
    // SEND AJAX POST REQUEST
    update_search()
  }

  /*
  * This method is called when a category is clicked and updates the global items object accordingly.
  * It then calls the post method (see update_search).
  */
  toggle_page = page => {
    
    // SET NEW PAGE
    st['result']['pages']['page'] = page
    
    // SEND AJAX POST REQUEST
    update_search()
  }

  /**
   * This method refreshes all Django templates on the search-results page
   */
  refresh_results = data => {
    
    // UPDATE HTML AND ITEMS OBJECT
    $('#search_result').empty().html(data['search_result'])
    $('#search_stats').empty().html(data['search_stats'])
    $('#search_params').empty().html(data['search_params'])
    $('#search_pagination').empty().html(data['search_pagination'])
    $('#search_options').empty().html(data['search_options'])
    $('#search_categories').empty().html(data['search_categories'])
    $('#search_facets').empty().html(data['search_facets']).foundation()
    $('#search_MET').empty().html(data['search_MET']).foundation()

    // SET GLOBALS
    user = data['user'], st = data['search']

    // SET DATE SLIDER IF NECESSARY
    setSlider()

    // POPULATE MET IF NECESSARY
    populate_MET()
  }

  // $('#METfilter').on('keyup', e => {
  //   console.log($(e.currentTarget).val())
  // })

  /* MET DROP METHOD */
  drop = e => {
    e.preventDefault()
    MET_term = JSON.parse(e.dataTransfer.getData("MET_term"))
    if ($("#METfilterList").find("#list_" + MET_term.code).length == 0) {
      li = $('<li>')
      .attr('id', 'list_' + MET_term.code)
      .append(
        $('<a>')
        .attr('href', '#')
        .text(MET_term.term)
      )
      .on('click', e => {
        $(e.currentTarget).remove()
        // $("#METfilterList").find("#list_" + MET_term.code).remove()
        st['MET']['MET_paths'] = st['MET']['MET_paths'].filter(obj => obj.code !== MET_term.code)
        update_search()
      })
      
      children = $('#METfilterList')

      $('#METfilterList').append(li)
      st['MET']['MET_paths'].push(MET_term)
      update_search()
    }
  }

  /*
  * This method posts a new AJAX request to the server and processes the response. 
  * The response contains an updated items object as well as partials rendered in HTML that are loaded in
  * individual tags in the search-results.html template.
  */
  update_search = () => {
    $.post('/mygiza/search/update', { 'search' : JSON.stringify(st) } )
    .done(response => {
      refresh_results(response)

      // LOAD CONTENT IN MODAL
      // $.ajax('/url')
      //   .done(function(resp){
      //     $modal.html(resp).foundation('open');
      // })       
    })
    .fail(response => {
      console.log(response)

    })
  }

  /* BIND METHODS TO THE DOM */
  $(document)
  .on('change', '#showResults', e => {
    console.log(e)
    st['result']['size'] = parseInt($(e.currentTarget).val())
    update_search()
  })
  .on('change', '#sortResults', e => {
    console.log(e)
    st['result']['sort'] = $(e.currentTarget).val()
    update_search()
  })
  .on('change', '#sortOrder', e => {
    console.log(e)
    st['result']['sort_order'] = $(e.currentTarget).val()
    update_search()
  })
  .on('click', '#addToCollectionBtn', e => $('#add_collection').find('a').data('object-name', $(e.currentTarget).data('id')))
  .on('click', '.add_to_collection_modal', e => {
    $.post({
      url : 'add-to-collection',
      data : {
        'collection' : $(e.currentTarget).data('collection-id'),
        'object' : JSON.stringify($(e.currentTarget).data('object-name')) 
      },
      success : response => {
        if (response.success) {
          console.log(response)
        }
        
        // $('#exampleModal3').foundation('reveal', 'open')
        // modal = new Foundation.Reveal($('.add_to_collection_modal'))
        // modal.close()
        // SOMEHOW MARK OBJECTS THAT ARE ALREADY IN A COLLECTION?
      }
    })
  })

  $(document).on('click', '#saveSearch', () => {
    console.log('save')
    input = prompt("Please give a name to this search", "Simple")
    if (input != null || input != '') {
      $.post({
        url: '/mygiza/search/save',
        data: {
          'name' : input,
          'search' : JSON.stringify(st)
          // 'term' : json.stringify(st['term']),
          // 'category' : json.stringify(st['category']),
          // 'fields' : JSON.stringify(st['fields']),
          // 'MET' : st['MET']
        },
        // contentType: "application/json",
        // dataType: 'json',
        success: data => {
          alert('search saved')
        },
        error: res => {
          console.log(res.responseText)
        }
      })
    }
  })

  $(document).on('keyup', '#search_token', e => {
    if (e.which == 13){
      $('#search_token_form').submit()
    }
  })

  // REQUEST ALL PRIVATE COLLECTIONS
  $(document).on('click', '.collections_content', e => {
    console.log('click')
    // id = $(e.currentTarget).attr('id')
    // $.get({
    //   url : '',
    // success : response => {
    //   $('#collections').empty().html(response[''])
    // }
      
    // })
  })

  $(document).on('click', '#reset_facets', e => {
    st['facets'].map(e => e)
    
  })

  $(document).on('click', '#redeem_token', e => {
    $.post("/mygiza/search/lookup/", { 'token' : $('#token').val() })
    .done(response => {
      (response.success) ? refresh_results(response.response) : alert(response.response)
      $('#token').val('')
    })
    .fail(response => {
      console.log(response, 2)
    })
    // success = response => {
    //   console.log(response)
    //   // refresh_results(response)
    // },
    // error = response => {
    //   console.log(response)
    // })
  })

  // $('#search_pagination select').on('change', e => {
  //   st['result']['size'] = parseInt($(e.currentTarget).val())
  //   console.log('resultsize')
  //   update_search()
  // })

  $('.add_to_collection').on('click', e => {
    console.log('click')
  })

  /* Drag and drop for MET */
  drag = (e, code, term) => e.dataTransfer.setData("MET_term", JSON.stringify({ 'code': code, 'term' : term }))
  allowDrop = e => e.preventDefault()

  // $('#sortResults').on('change', e => {
  //   st['result']['sort'] = $(e.currentTarget).val()
  //   update_search()
  // })


    /*
    * IF SEARCH TERMS ARE DEFINED ON THE PAGE (I.E. THE USER HAS SEARCH RESULTS TO PLAY WITH)
    */
    if (typeof st !== 'undefined') {

      // POPULATE MET LIST FILTER AUTOCOMPLETE BOX
      populate_MET = () => {

        if ('MET_terms' in st['MET'] && st['MET']['MET_terms'].length) {
          MET_list = st['MET']['MET_terms'].map(e => e.Term)

          // $('#METfilter').autocomplete({ 
          //   source : MET_list,
          //   minLength:2,
          //   position: { my : "center", at: "center", of: "#METfilter" }, 
          //   select: (e, ui) => { 
          //     console.log(e, ui)
          //     // goTo(ui.item.value)
          //     // return false
          //   }         
          // })

          for (idx in st['MET']['MET_paths']) {
            li = $('<li>')
            .attr('id', 'list_' + st['MET']['MET_paths'][idx].code)
            .append(
              $('<a>')
              .attr('href', '#')
              .text(st['MET']['MET_paths'][idx].term)
            ).on('click', e => {
              $(e.currentTarget).remove()
              st['MET']['MET_paths'] = st['MET']['MET_paths'].filter(obj => obj.code !== $(e.currentTarget).attr('id').substring(5))
              update_search()
            })
            $('#METfilterList').append(li)
          }
        }
      }

      // Set date slider as a facet
      setSlider = () => {

        // SET SLIDER TICKS
        setSliderTicks = (minimum, maximum) => {
          let $slider = $('#slider-range').find('.ui-slider-tick-mark').remove()
          $('<span class="ui-slider-tick-mark"></span>').text(minimum).css('left', '-15px').appendTo($slider)
          $('<span class="ui-slider-tick-mark"></span>').text(maximum).css('right', '15px').appendTo($slider)
        }

        /*
        Construct a date slider
        @param max_range: range of slider, array of integers
        @param value_range : range to set handles, array of integers
        */
        makeSlider = (max_range, value_range) => {
          $('#date_slider_from').text(new Date(value_range[0] * 1000).toDateString())
          $('#date_slider_to').text(new Date(value_range[1] * 1000).toDateString())
          $("#slider-range").slider({
            range : true,
            min : max_range[0],
            max : max_range[1],
            step: 1,
            values: value_range,
            slide: (event, ui) => {
              $('#date_start').val(ui.values[0])
              $('#date_end').val(ui.values[1])
              $('#date_slider_from').text(new Date(ui.values[0] * 1000).toDateString())
              $('#date_slider_to').text(new Date(ui.values[1] * 1000).toDateString())
            },
            change: () => {
              st['fields']['entrydates_ms'] = [parseInt($('#date_start').val()), parseInt($('#date_end').val())]
              update_search()
            }
          })
          setSliderTicks(new Date(max_range[0] * 1000).getFullYear(), new Date(max_range[1] * 1000).getFullYear())
        }

        // IF ADVANCED SEARCH INCLUDED DATE
        if ('entrydate_ms' in st['fields'] && st['fields']['entrydate_ms'].length) {
          
          if ('entrydates_ms' in st['fields']) {
            minimum_set_value = st['fields']['entrydates_ms'][0]
            maximum_set_value = st['fields']['entrydates_ms'][1]
            max_range = st['fields']['entrydate_ms']
          } else {
            minimum_set_value = st['fields']['entrydate_ms'][0]
            maximum_set_value = (typeof st['fields']['entrydate_ms'][1] !== 'undefined') ? st['fields']['entrydate_ms'][1] : 0
            max_range = st['fields']['entrydate_ms']
          }
          
        } else {

          dateRange = Object.keys(st['facets']).filter(key => key.includes('_daterange'))

          if (dateRange.length) {
            range = st['facets'][dateRange].map(i => parseInt(i['display_text'])).sort((a, b) => a - b)
            max_range = [range[0], range[range.length - 1 ]]

            // SEARCH DID NOT INITIALLY INCLUDE A DATE; ENTRYDATES_MS PARAMETERS IN ST AT NEXT REQUEST
            if ('entrydates_ms' in st['fields']) {
              minimum_set_value = st['fields']['entrydates_ms'][0]
              maximum_set_value = st['fields']['entrydates_ms'][1]
            } else {
              minimum_set_value = max_range[0]
              maximum_set_value = max_range[1]
            }
          }
        }

        if (typeof max_range !== 'undefined') {
          console.log(max_range)
          if (max_range.length && minimum_set_value && maximum_set_value) {
            makeSlider(max_range, [minimum_set_value, maximum_set_value])
          }
        }
      }

      setSlider()
    }
})