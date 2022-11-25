$(document).foundation()

// Smooth scroll for in-page anchors
// Src: https://css-tricks.com/snippets/jquery/smooth-scrolling/

$(document).ready(() => {

  // SHOW DEFAULT ADVANCED SEARCH OPTION
  selected_option = $('input[name="category"]:checked').attr('data-for-id')
  if (!$($('#'+selected_option)).is(':visible')) showHideMenu($('#'+selected_option).attr('id'))

  // Variable set to accommodate fixed-top navbar.
  // Un-comment the appropriate value below.
  let topOffset = 99
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

// ADVANCED SEARCH: SHOW/HIDE SECTIONS FOR SEARCHING IN CATEGORIES
$('fieldset#category-radio-selector input').click(e => showHideMenu(e))

// FUNCTION TO SHOW/HIDE SECTIONS FOR THE MENU
showHideMenu = e => {
  if (e != undefined) {
    // RETAIN REFERENCE FOR CURRENT CATEGORY
    selected_option = $('input[name="category"]:checked').val()
    
    $('#advanced-search-form').trigger("reset") // RESET THE SEARCH FORM WHEN CHANGING SEARCH OPTION
    $('.category-section').hide()               // HIDE THE SECTIONS
   
    // DETERMINE TARGET SECTION
    target = e.type == "click" ? $(e.currentTarget).attr('data-for-id') : e
    
    // SHOW RELEVANT ITEMS
    $('#'+selected_option).prop('checked', true)
    $('#'+target).show()                        // SHOW RELEVANT SECTION ONLY
  }
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