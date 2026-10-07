    // --- the cabinet's live preview (data-preview="live") -------------------

    // The Channels page frames the hosted chat page of its own origin and
    // sends the colour, corner, language and theme the owner is choosing, before
    // anything is saved; the preview says when it is ready for them. Typing
    // is shown but goes nowhere (the Try tab is for test conversations).
    function showAsPreview() {
      input.readOnly = true;
      composer.setAttribute("aria-disabled", "true");
      window.addEventListener("message", function (event) {
        var data = event.data;
        if (
          event.source !== window.parent ||
          event.origin !== window.location.origin ||
          !data ||
          typeof data !== "object" ||
          data.type !== PREVIEW_LOOK_MESSAGE
        ) {
          return;
        }
        guarded("render", applyPreviewLook)(data);
      });
      if (window.parent !== window) {
        window.parent.postMessage({ type: PREVIEW_READY_MESSAGE }, window.location.origin);
      }
    }

    function applyPreviewLook(look) {
      paintAccent(chooseAccent(look.color, config.accent_color));
      var theme = chooseTheme(look.theme);
      if (theme) {
        wrapper.classList.toggle("aw-light", theme === "light");
        wrapper.classList.toggle("aw-dark", theme === "dark");
      }
      var isLeft = choosePosition(look.position, config.position) === "left";
      wrapper.classList.toggle("aw-left", isLeft && !isPageMode);
      var tags = (Array.isArray(config.languages) ? config.languages : []).map(function (language) {
        return String(language.tag);
      });
      var language = matchLanguage(String(look.language || ""), tags);
      if (language && language !== state.language) {
        state.language = language;
        if (languageSelect) {
          languageSelect.value = language;
        }
        applyLanguage();
      }
    }

    // The business's colour on the header, launcher and send button, made
    // readable (accentColors); none chosen: the widget's own clay.
    function paintAccent(accent) {
      if (!accent) {
        return;
      }
      var colors = accentColors(accent);
      wrapper.style.setProperty("--aw-accent", colors.accent);
      wrapper.style.setProperty("--aw-on-accent", colors.onAccent);
    }
