$(document).foundation();

// Retrigger orbit in interchange after loaded
/*
$("#hero-home").on("replaced.zf.interchange", function() {
  if ($('[data-orbit]').length) {
    var orbits = new Foundation.Orbit($('[data-orbit]'));
  }
});
*/

// Accordion menu toggletext

$('[data-accordion-menu]').on('down.zf.accordionMenu', function(){
  var toggleItem = $(this).find('.accordion-toggletext');
  var openText = toggleItem.attr('data-open-text');
  toggleItem.text(openText);
}).on('up.zf.accordionMenu', function(){
  var toggleItem = $(this).find('.accordion-toggletext');
  var closedText = toggleItem.attr('data-closed-text');
  toggleItem.text(closedText);
});