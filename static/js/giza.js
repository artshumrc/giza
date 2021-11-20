$(document).foundation()

// window.Foundation

// Smooth scroll for in-page anchors
// Src: https://css-tricks.com/snippets/jquery/smooth-scrolling/

$(document).ready(() => {

  // SHOW DEFAULT ADVANCED SEARCH OPTION
  selected_option = $('input.advanced_search_field:checked').attr('data-for-id')
  if (!$($('#'+selected_option)).is(':visible')) showHideMenu($('#'+selected_option).attr('id'))
  addHidden($('#'+selected_option))

  // Variable set to accommodate fixed-top navbar.
  // Un-comment the appropriate value below.
  //topOffset = 70; // Normal, no extra banner
  // topOffset = 99; // With extra under-construction banner

  /**
   *
   * Currently throwing errors whenever links are clicked, investigate in future releases
   *
  $('a[href*="#"]:not([href="#0"])').click(function() {
    if (location.pathname.replace(/^\//,'') == this.pathname.replace(/^\//,'') && location.hostname == this.hostname) {
      var target = $(this.hash);
      target = target.length ? target : $('[name=' + this.hash.slice(1) +']');
      if (target.length) {
        $('html, body').animate({
          scrollTop: (target.offset().top - topOffset)
        }, 600);
        return false;
      }
    }
  });
  */

  // This method adds parameters to hidden fields in the post form to hide them in the URL
  $('input.advanced_search_field').on('change', e => addHidden($(e.currentTarget)))

  $('#advanced-search-form-btn').on('click', e => {
    $('.advanced_search_field').removeAttr('name')
    $('#advanced-search-form').submit()
  })







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
    idx = st['facets'][facet[0]].map(e => e.display_text).indexOf(facet[1])
    st['facets'][facet[0]][idx]['selected'] = !st['facets'][facet[0]][idx]['selected']

    // SEND AJAX POST REQUEST
    update_search()
  }

  /*
  * This method is called when a category is clicked and updates the global items object accordingly.
  * It then calls the post method (see update_search).
  */
  toggle_category = category => {

    // RESET THE PAGE FOR VIEWING
		st['result']['pages']['page'] = 1
    
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
    console.log(st)
    
    // SEND AJAX POST REQUEST
    update_search()
  }

  /*
  * This method is called when a new MET term is added to the filter box. The method then calls the update_search method.
  */
  drop = e => {
    e.preventDefault()
    id = $('#' + e.dataTransfer.getData("text")).attr('id')
    console.log(id)
    
    newNode = document.getElementById(id).cloneNode(true)
    $(newNode).attr('id', 'list_' + id)
    
    $(newNode).on('click', e => {
      console.log($(e.currentTarget))
      $(e.currentTarget).remove()
      idx = st['MET']['MET_paths'].indexOf(id)
      if (index !== -1) {
        st['MET']['MET_paths'].splice(idx, 1)
      }
    })
    
    e.target.appendChild(newNode)
    if (!st['MET']['MET_paths'].includes(id)) {
      st['MET']['MET_paths'].push(id)
    }
    
    update_search()
  }

    /*
  * Drop for MET
  */
  // drop = ev => {
  //   ev.preventDefault()
  //   id = $('#'+ev.dataTransfer.getData("text")).attr('id')
  //   newNode = document.getElementById(id).cloneNode(true)
  //   $(newNode).attr('id', 'list_'+id)
    
  //   $(newNode).on('click', e => {
  //     console.log($(e.currentTarget))
  //     $(e.currentTarget).remove()
  //   })

  //   ev.target.appendChild(newNode)
    
  //   if (!ml.includes(id)) {
  //     ml.push(id)
  //   }
  //   document.getElementById('MET_form').submit()
  // }

  /*
  * This method posts a new AJAX request to the server and processes the response. 
  * The response contains an updated items object as well as partials rendered in HTML that are loaded in
  * the individual tags in the search-results.html template.
  */
  update_search = () => {
    $.post({
      url : '/search/update',
      data : { 'search' : JSON.stringify(st) } },
      success = response => {
        
        // UPDATE HTML AND ITEMS OBJECT
        $('#search_result').empty().html(response['search_result'])
        $('#search_stats').empty().html(response['search_stats'])
        $('#search_params').empty().html(response['search_params'])
        $('#search_pagination').empty().html(response['search_pagination'])
        $('#search_categories').empty().html(response['search_categories'])
        $('#search_facets').empty().html(response['search_facets']).foundation()
        $('#search_MET').empty().html(response['search_MET']).foundation()
        st = response['search']
      }
    )
  }

  /*
  * Drag for MET
  */
  drag = ev => {
    console.log(ev.target.id)
    ev.dataTransfer.setData("text", ev.target.id)
  }

  // toggle the signup/login forms in the auth modal
  $(".login-toggle").on("click", () => {
    $(".modal .login-form").hide()
    $(".modal .signup-form").show()
  })

  $(".signup-toggle").on("click", () => {
    $(".modal .login-form").show()
    $(".modal .signup-form").hide()
  })

  // Start 3D environment
  $(".giza3dEmbedToggle").click(() => {
    $(".giza3dEmbedToggle").hide()
    $(".giza3dEmbed").show()
  })
})

// This convenience method loads HTML data in the search_pages div (see search.html)
loadPage = data => $('#search_pages').html(data)

// ADVANCED SEARCH: SHOW/HIDE SECTIONS FOR SEARCHING IN CATEGORIES
$('fieldset#category-radio-selector input').click(e => showHideMenu(e))

// This function shows/hides parts of the advanced search categories
showHideMenu = e => {
  if (e != undefined) {
    // RETAIN REFERENCE OF CURRENT CATEGORY
    selected_option = $('input.advanced_search_field:checked').val()
    
    $('#advanced-search-form').trigger("reset") // RESET THE SEARCH FORM WHEN CHANGING SEARCH OPTION
    $('.category-section').hide()               // HIDE THE SECTIONS
   
    // DETERMINE TARGET SECTION
    target = e.type == "click" ? $(e.currentTarget).attr('data-for-id') : e
    
    // SHOW RELEVANT ITEMS
    $('#'+selected_option).prop('checked', true)
    $('#'+target).show()                        // SHOW RELEVANT SECTION ONLY
  }
}

addHidden = elem => {
  hidden = $('<input>').attr('type', 'hidden').addClass('hidden_field').attr('name', elem.attr('name')).val(elem.val())

  if (elem.parent().find(`.hidden_field[name=${elem.attr('name')}]`).length) {
    console.log('removing')
    elem.parent().find(`.hidden_field[name=${elem.attr('name')}]`).remove()
  }

  elem.parent().append(hidden)
}


// Accordion menu toggletext

$('[data-accordion-menu]')

.on('down.zf.accordionMenu', () => {
  let toggleItem = $(this).find('.accordion-toggletext')
  toggleItem.text(toggleItem.attr('data-open-text'))
})

.on('up.zf.accordionMenu', () => {
  let toggleItem = $(this).find('.accordion-toggletext')
  toggleItem.text(toggleItem.attr('data-closed-text'))
})

// Top bar Search dropdown behavior

$('#search-dropdown').on('show.zf.dropdown', () => {
  
  $('[data-toggle="search-dropdown"]').addClass('is-active')
  
  setTimeout(() => { $('#inputSimpleSearch').focus() }, 250)
})

.on('hide.zf.dropdown', () => {
  let trigger = $('[data-toggle="search-dropdown"]')
  trigger.removeClass('is-active')
  setTimeout(() => { trigger.blur() }, 250)
})

// Dynamically adjust right-column margin on feature full view

fnAdjustRightColMargin = () => {
  let offset = Foundation.Box.GetDimensions($('#jumpmenu'))['height']
  offset = (offset + 50)
  $('.header-full.mode-full .content-col-secondary').css('margin-top', offset)
}

// Only run this function on ready if #jumpmenu is present
if ($('#jumpmenu').length) {
  fnAdjustRightColMargin()
}