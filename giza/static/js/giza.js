$(document).foundation();

// Smooth scroll for in-page anchors
// Src: https://css-tricks.com/snippets/jquery/smooth-scrolling/

$(function() {
  $('a[href*="#"]:not([href="#0"])').click(function() {
    if (location.pathname.replace(/^\//,'') == this.pathname.replace(/^\//,'') && location.hostname == this.hostname) {
      var target = $(this.hash);
      target = target.length ? target : $('[name=' + this.hash.slice(1) +']');
      if (target.length) {
        $('html, body').animate({
          scrollTop: (target.offset().top - 70)
        }, 600);
        return false;
      }
    }
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

