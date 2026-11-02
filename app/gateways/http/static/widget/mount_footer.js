    // --- the footer: AI note, privacy, accessibility, "Powered by" --------

    function buildFooter() {
      var row = el("p", "aw-footer");
      var note = el("span", "");
      row.appendChild(note);
      var privacy = null;
      if (typeof config.privacy_url === "string" && WEB_LINK_PATTERN.test(config.privacy_url)) {
        row.appendChild(document.createTextNode(" · "));
        privacy = footerLink("aw-privacy", config.privacy_url, "noopener noreferrer");
        row.appendChild(privacy);
      }
      // The platform's accessibility statement, in the visitor's language
      // (the API sends the browser to the public site's page).
      row.appendChild(document.createTextNode(" · "));
      var accessibility = footerLink("aw-accessibility", accessibilityUrl(), "noopener noreferrer");
      row.appendChild(accessibility);
      // "Powered by" with the business's referral code (gone on Plus when
      // the owner turned it off: the config then has no link).
      var powered = null;
      if (typeof config.powered_by_url === "string" && WEB_LINK_PATTERN.test(config.powered_by_url)) {
        row.appendChild(document.createTextNode(" · "));
        powered = footerLink("aw-powered", config.powered_by_url, "noopener");
        row.appendChild(powered);
      }
      return {
        row: row,
        note: note,
        privacy: privacy,
        accessibility: accessibility,
        powered: powered
      };
    }

    // A link of the footer: only a web address, always in a new tab that
    // cannot reach back to this page.
    function footerLink(className, url, rel) {
      var link = el("a", className);
      if (isSafeWebLink(url)) {
        link.href = url;
      }
      link.target = "_blank";
      link.rel = rel;
      return link;
    }

    function accessibilityUrl() {
      return apiBase + ACCESSIBILITY_PATH + "?language=" + encodeURIComponent(state.language);
    }

    // The footer's texts (and the statement's language) in the interface
    // language.
    function applyFooterLanguage() {
      footer.note.textContent = text("footer");
      if (footer.privacy) {
        footer.privacy.textContent = text("privacy");
      }
      footer.accessibility.textContent = text("accessibility");
      footer.accessibility.href = accessibilityUrl();
      if (footer.powered) {
        footer.powered.textContent = text("poweredBy");
      }
    }
