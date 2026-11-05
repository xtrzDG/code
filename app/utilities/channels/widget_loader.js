/*! Assistant Workshop website chat: loader. Loads the current chat widget
    (widget.js, next to this file's /widget/v/ folder) with the settings
    of this script tag. This file never changes once published: the embed
    code pins it with an integrity hash. */
(function () {
  "use strict";

  var VERSIONS_FOLDER = "/widget/v/";
  var WIDGET_FILE = "/widget.js";
  var POLICY_NAME = "assistant-workshop-widget";

  var own = document.currentScript;
  if (!own || own.tagName !== "SCRIPT") {
    return;
  }

  var source;
  try {
    source = new URL(own.src, window.location.href);
  } catch (error) {
    return;
  }

  var at = source.pathname.lastIndexOf(VERSIONS_FOLDER);
  if (at < 0) {
    return;
  }

  var widgetUrl = source.origin + source.pathname.slice(0, at) + WIDGET_FILE;
  var widget = document.createElement("script");
  for (var index = 0; index < own.attributes.length; index += 1) {
    var attribute = own.attributes[index];
    if (attribute.name.indexOf("data-") === 0) {
      widget.setAttribute(attribute.name, attribute.value);
    }
  }
  widget.async = true;
  // A site whose Content Security Policy allows scripts by nonce allows
  // the widget this tag loads, too.
  if (own.nonce) {
    widget.nonce = own.nonce;
  }

  try {
    widget.src = trustedUrl(widgetUrl);
  } catch (error) {
    if (window.console && window.console.warn) {
      window.console.warn("[Assistant Workshop chat] this page's Trusted Types policy blocks the chat.");
    }
    return;
  }

  if (own.parentNode) {
    own.parentNode.insertBefore(widget, own.nextSibling);
  } else {
    (document.head || document.documentElement).appendChild(widget);
  }

  // Pages that enforce Trusted Types get a policy that allows only this URL.
  function trustedUrl(url) {
    var types = window.trustedTypes;
    if (!types || typeof types.createPolicy !== "function") {
      return url;
    }
    try {
      return types
        .createPolicy(POLICY_NAME, {
          createScriptURL: function (candidate) {
            if (candidate !== url) {
              throw new TypeError("Only the chat widget may be loaded.");
            }
            return candidate;
          },
        })
        .createScriptURL(url);
    } catch (error) {
      return url;
    }
  }
})();
