(function () {
  // Triiiceratops 1.0 registers plugin factories into the shared, order-independent
  // `window.Triiiceratops.plugins` registry, keyed by package name. (The pre-1.0
  // `window.TriiiceratopsPlugins` globals were removed.) Registering does not
  // activate anything — each viewer opts in by assigning `viewer.plugins`.
  var PLUGIN_PACKAGES = [
    '@triiiceratops/plugin-image-export',
    '@triiiceratops/plugin-image-manipulation',
  ];

  function configureTriiiceratopsPlugins(root) {
    var runtime = window.Triiiceratops;
    if (!runtime || !runtime.plugins) return;

    var pluginList = PLUGIN_PACKAGES.map(function (name) {
      return runtime.plugins.get(name);
    }).filter(Boolean);
    if (!pluginList.length) return;

    var viewers = (root || document).querySelectorAll('triiiceratops-viewer');
    for (var i = 0; i < viewers.length; i += 1) {
      viewers[i].plugins = pluginList;
    }
  }

  window.configureTriiiceratopsPlugins = configureTriiiceratopsPlugins;

  if (window.customElements && window.customElements.whenDefined) {
    window.customElements.whenDefined('triiiceratops-viewer').then(function () {
      configureTriiiceratopsPlugins(document);
    });
  } else {
    configureTriiiceratopsPlugins(document);
  }
})();
