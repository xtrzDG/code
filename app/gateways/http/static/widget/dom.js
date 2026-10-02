  // --- DOM helpers -------------------------------------------------------

  function findOwnScript() {
    if (document.currentScript && document.currentScript.tagName === "SCRIPT") {
      return document.currentScript;
    }
    var scripts = document.getElementsByTagName("script");
    for (var index = scripts.length - 1; index >= 0; index -= 1) {
      var candidate = scripts[index];
      var source = candidate.getAttribute("src") || "";
      if (
        candidate.hasAttribute(BUSINESS_ATTRIBUTE) &&
        source.split("?")[0].slice(-SCRIPT_FILE_NAME.length) === SCRIPT_FILE_NAME
      ) {
        return candidate;
      }
    }
    return null;
  }

  function resolveApiBase(scriptTag) {
    var configured = scriptTag.getAttribute("data-api-base");
    var base = configured;
    if (!base) {
      try {
        var source = new URL(scriptTag.src, window.location.href);
        var path = source.pathname;
        var prefix = path.slice(0, path.length - SCRIPT_FILE_NAME.length);
        base = source.origin + (path.slice(-SCRIPT_FILE_NAME.length) === SCRIPT_FILE_NAME ? prefix : "");
      } catch (error) {
        base = "";
      }
    }
    return String(base).replace(/\/+$/, "");
  }

  function applyStyles(root) {
    // Constructable stylesheets also work on pages whose Content-Security-
    // Policy forbids inline <style> elements.
    try {
      if (root.adoptedStyleSheets !== undefined && typeof CSSStyleSheet === "function") {
        var sheet = new CSSStyleSheet();
        sheet.replaceSync(CSS);
        root.adoptedStyleSheets = [sheet];
        return;
      }
    } catch (error) {
      // Fall back to a <style> element below.
    }
    var style = document.createElement("style");
    style.textContent = CSS;
    root.appendChild(style);
  }

  function messageRow(role, messageText, direction, authorLabel) {
    var row = el("div", "aw-message aw-" + role);
    if (authorLabel) {
      // The label is in the interface language; the message keeps its own
      // direction below it.
      var author = el("span", "aw-author");
      author.textContent = authorLabel;
      row.appendChild(author);
    }
    var body = el("div", "");
    // Each message finds its own direction (a Hebrew reply in an English
    // interface, a phone number in an Arabic one). A business message the
    // API marks right-to-left stays right-to-left even when it opens with a
    // Latin name ("Pizza Roma مفتوح ..."), as long as it has right-to-left
    // letters; "ltr" is never forced (the API also sends it for unknown
    // languages).
    var isRightToLeft =
      role !== "visitor" && direction === "rtl" && RTL_CHARACTER_PATTERN.test(messageText);
    body.setAttribute("dir", isRightToLeft ? "rtl" : "auto");
    if (direction === "rtl" || direction === "ltr") {
      body.setAttribute("data-language-direction", direction);
    }
    appendLinkedText(body, messageText);
    row.appendChild(body);
    return row;
  }

  function appendLinkedText(parent, messageText) {
    var lastIndex = 0;
    var match;
    URL_PATTERN.lastIndex = 0;
    while ((match = URL_PATTERN.exec(messageText)) !== null) {
      var url = match[0].replace(/[.,;:!?)\]]+$/, "");
      if (match.index > lastIndex) {
        parent.appendChild(document.createTextNode(messageText.slice(lastIndex, match.index)));
      }
      var link = document.createElement("a");
      link.href = url;
      link.textContent = url;
      link.target = "_blank";
      link.rel = "noopener noreferrer nofollow";
      parent.appendChild(link);
      lastIndex = match.index + url.length;
      URL_PATTERN.lastIndex = lastIndex;
    }
    if (lastIndex < messageText.length) {
      parent.appendChild(document.createTextNode(messageText.slice(lastIndex)));
    }
  }

  function el(tagName, className) {
    var element = document.createElement(tagName);
    if (className) {
      element.className = className;
    }
    return element;
  }

  function svgIcon(paths) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    paths.forEach(function (definition) {
      var path = document.createElementNS(SVG_NS, "path");
      path.setAttribute("d", definition);
      svg.appendChild(path);
    });
    return svg;
  }

  function chatIcon() {
    return svgIcon(["M21 12a8 8 0 0 1-11.8 7.04L4 20l1.05-4.2A8 8 0 1 1 21 12z"]);
  }

  function closeIcon() {
    return svgIcon(["M6 6l12 12", "M18 6L6 18"]);
  }

  function sendIcon() {
    return svgIcon(["M4 12l16-8-6 16-2.5-6.5L4 12z", "M11.5 13.5L20 4"]);
  }

  function readableTextColor(hexColor) {
    var hex = hexColor.slice(1);
    if (hex.length === 3) {
      hex = hex.charAt(0) + hex.charAt(0) + hex.charAt(1) + hex.charAt(1) + hex.charAt(2) + hex.charAt(2);
    }
    var channels = [0, 2, 4].map(function (offset) {
      var value = parseInt(hex.slice(offset, offset + 2), 16) / 255;
      return value <= 0.03928 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
    });
    var luminance = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
    // The higher WCAG contrast: with white 1.05/(L+0.05), with #111827
    // (L about 0.0093) (L+0.05)/0.0593.
    return 1.05 / (luminance + 0.05) >= (luminance + 0.05) / 0.0593 ? "#ffffff" : "#111827";
  }

  function warn(message) {
    if (window.console && window.console.warn) {
      window.console.warn("[Assistant Workshop chat] " + message);
    }
  }

  function info(message) {
    if (window.console && window.console.info) {
      window.console.info("[Assistant Workshop chat] " + message);
    }
  }
})();
