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

// from http://jsfiddle.net/iambriansreed/bjdSF/ and http://stackoverflow.com/a/5454303
$(function() {
  var minimized_elements = $('span.minimize');

  minimized_elements.each(function(){
    var t = $(this).text(),
    max_length = 200;

    if(t.length < max_length) return;

    var trimmed_string = t.substr(0, max_length);
    max_length = Math.min(trimmed_string.length, trimmed_string.lastIndexOf(" "));
    trimmed_string = trimmed_string.substr(0, max_length);

    $(this).html(
      trimmed_string+'<span> ... </span><a href="#" class="more">More</a>'+
      '<span style="display:none;">'+ t.substr(max_length,t.length)+' <a href="#" class="less">Less</a></span>'
    );

  });

  $('a.more', minimized_elements).click(function(event){
    event.preventDefault();
    $(this).hide().prev().hide();
    $(this).next().show();
  });

  $('a.less', minimized_elements).click(function(event){
    event.preventDefault();
    $(this).parent().hide().prev().show().prev().show();
  });

});

// Dynamically adjust right-column margin on feature full view

var fnAdjustRightColMargin = function() {
  var menu = $('#jumpmenu');
  if (menu.length > 0) {
    var col = $('.header-full.mode-full .content-col-secondary');
    var offset = Foundation.Box.GetDimensions(menu)['height'];
    offset = (offset + 50);
    col.css('margin-top', offset);
  }
}

fnAdjustRightColMargin();
