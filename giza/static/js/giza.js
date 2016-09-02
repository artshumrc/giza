$(document).foundation();
// retrigger orbit in interchange after loaded
$("#hero-home").on("replaced.zf.interchange", function() {
  if ($('[data-orbit]').length) {
    var orbits = new Foundation.Orbit($('[data-orbit]'));
  }
});
