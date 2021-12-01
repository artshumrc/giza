$(document).foundation()

// Smooth scroll for in-page anchors
// Src: https://css-tricks.com/snippets/jquery/smooth-scrolling/

$(document).ready(() => {

  // CATCHING TOKEN
  csrftoken = $("[name=csrfmiddlewaretoken]").val()      
  csrfSafeMethod = method => /^(GET|HEAD|OPTIONS|TRACE)$/.test(method)
  
  // APPEND CSRF TOKENS TO ALL AJAX POST REQUESTS
  $.ajaxSetup({
    beforeSend: (xhr, settings) => {
      if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
        xhr.setRequestHeader("X-CSRFToken", csrftoken)
      }
    }
  })


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
$('#search-dropdown')
  .on('show.zf.dropdown', () => {
    $('[data-toggle="search-dropdown"]').addClass('is-active')
    setTimeout(() => { $('#inputSimpleSearch').focus() }, 250)
  })
  .on('hide.zf.dropdown', () => {
    let trigger = $('[data-toggle="search-dropdown"]')
    trigger.removeClass('is-active')
    setTimeout(() => { trigger.blur() }, 250)
  })

// $("#dateSlider").on('change changed.zf.slider', () => {
//   console.log('slide')
// })

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

  // Variable set to accommodate fixed-top navbar.
  // Un-comment the appropriate value below.
  // topOffset = 70; // Normal, no extra banner
  // topOffset = 99; // With extra under-construction banner

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