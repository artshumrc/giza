(function () {
  function configureTriiiceratopsPlugins(root) {
    var plugins = window.TriiiceratopsPlugins;
    if (!plugins) return;

    var pluginList = [plugins.ImageDownload, plugins.ImageManipulation].filter(Boolean);
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
