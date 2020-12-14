$(document).foundation();

// Smooth scroll for in-page anchors
// Src: https://css-tricks.com/snippets/jquery/smooth-scrolling/

$(function() {

  // Variable set to accommodate fixed-top navbar.
  // Un-comment the appropriate value below.
  var topOffset;
  //topOffset = 70; // Normal, no extra banner
  topOffset = 99; // With extra under-construction banner

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
  $(".login-toggle").on("click", function() {
    $(".modal .login-form").hide();
    $(".modal .signup-form").show();
  });
  $(".signup-toggle").on("click", function() {
    $(".modal .login-form").show();
    $(".modal .signup-form").hide();
  });

  // Start 3D environment
  $(".giza3dEmbedToggle").on("click", function() {
    $(".giza3dEmbedToggle").hide();
    $(".giza3dEmbed").show();
  });
});

// Accordion menu toggletext

$('[data-accordion-menu]').on('down.zf.accordionMenu', function() {
  var toggleItem = $(this).find('.accordion-toggletext');
  var openText = toggleItem.attr('data-open-text');
  toggleItem.text(openText);
}).on('up.zf.accordionMenu', function() {
  var toggleItem = $(this).find('.accordion-toggletext');
  var closedText = toggleItem.attr('data-closed-text');
  toggleItem.text(closedText);
});

// Top bar Search dropdown behavior

$('#search-dropdown').on('show.zf.dropdown', function() {
  $('[data-toggle="search-dropdown"]').addClass('is-active');
  setTimeout(function() {
    $('#inputSimpleSearch').focus();
  }, 250);
}).on('hide.zf.dropdown', function() {
  var trigger = $('[data-toggle="search-dropdown"]');
  trigger.removeClass('is-active');
  setTimeout(function() {
    trigger.blur();
  }, 250);
});

// Dynamically adjust right-column margin on feature full view

var fnAdjustRightColMargin = function() {
  var menu = $('#jumpmenu');
  var col = $('.header-full.mode-full .content-col-secondary');
  var offset = Foundation.Box.GetDimensions(menu)['height'];
  offset = (offset + 50);
  col.css('margin-top', offset);
}

// Only run this function on ready if #jumpmenu is present
if ($('#jumpmenu').length) {
  fnAdjustRightColMargin();
}

// on Advanced Search page, switch between search fields for different categories
$('fieldset#category-radio-selector input').click(function() {
  $('.category-section').hide();
  var section_id = $(this).attr('data-for-id');
  $('#'+section_id).show();
});
