  function mount(config, isPreview) {
    var showPreviewBanner = isPreview && !config.is_enabled;
    var host = document.createElement("div");
    host.setAttribute("data-assistant-workshop-chat", "");
    if (!host.attachShadow) {
      warn("this browser does not support the chat widget.");
      return;
    }
    var root = host.attachShadow({ mode: "open" });
    applyStyles(root);

    var state = {
      config: config,
      language: chooseLanguage(config),
      sessionKey: loadSessionKey(),
      history: loadHistory(),
      isOpen: false,
      isSending: false,
      pendingItem: null,
      handoffNoticeShown: false,
      // Polling for staff replies (see the header comment).
      cursor: storageGet(localStorageOrNull(), storagePrefix + "cursor"),
      isHandedOff: storageGet(localStorageOrNull(), storagePrefix + "handoff") === "1",
      handoffAt: Number(storageGet(localStorageOrNull(), storagePrefix + "handoff-at")) || 0,
      // The visitor's last exchange (an answer or new messages), any tab.
      activityAt: Number(storageGet(localStorageOrNull(), storagePrefix + "activity-at")) || 0,
      // The history as this tab last read or wrote it (other tabs change it).
      storedHistory: storageGet(localStorageOrNull(), storagePrefix + "history"),
      pollTimer: null,
      pollDelay: POLL_FIRST_DELAY_MS,
      isPolling: false,
      pollStopped: false,
      // Sending waits until then after a 429 (Date.now() milliseconds).
      sendHeldUntil: 0
    };
    state.handoffNoticeShown = state.history.some(function (item) {
      return item.role === "notice";
    });

    var accent = chooseAccent(script.getAttribute("data-color"), config.accent_color);
    var wrapper = el("div", "aw");
    if (accent) {
      wrapper.style.setProperty("--aw-accent", accent);
      wrapper.style.setProperty("--aw-on-accent", readableTextColor(accent));
    }
    if (choosePosition(script.getAttribute("data-position"), config.position) === "left") {
      wrapper.className += " aw-left";
    }

    var panelId = "aw-panel-" + Math.random().toString(36).slice(2);
    var launcher = el("button", "aw-launcher");
    launcher.type = "button";
    launcher.setAttribute("aria-controls", panelId);
    launcher.setAttribute("aria-expanded", "false");
    launcher.appendChild(chatIcon());
    launcher.appendChild(el("span", "aw-badge"));

    var panel = el("div", "aw-panel");
    panel.id = panelId;
    panel.hidden = true;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "false");

    var header = el("div", "aw-header");
    var heading = el("div", "aw-heading");
    var title = el("h2", "aw-title");
    title.textContent = config.business_name || "";
    title.setAttribute("dir", "auto");
    var subtitle = el("p", "aw-subtitle");
    heading.appendChild(title);
    heading.appendChild(subtitle);
    header.appendChild(heading);

    var languageSelect = null;
    var languages = Array.isArray(config.languages) ? config.languages : [];
    if (languages.length > 1) {
      languageSelect = el("select", "aw-language");
      languages.forEach(function (language) {
        var option = document.createElement("option");
        option.value = language.tag;
        option.textContent = pickerLabel(language);
        option.setAttribute("dir", language.direction === "rtl" ? "rtl" : "ltr");
        languageSelect.appendChild(option);
      });
      languageSelect.value = state.language;
      languageSelect.addEventListener("change", function () {
        state.language = languageSelect.value;
        storageSet(localStorageOrNull(), storagePrefix + "language", state.language);
        applyLanguage();
      });
      header.appendChild(languageSelect);
    }

    var closeButton = el("button", "aw-icon-button");
    closeButton.type = "button";
    closeButton.appendChild(closeIcon());
    closeButton.addEventListener("click", function () {
      setOpen(false);
    });
    header.appendChild(closeButton);
    panel.appendChild(header);

    var banner = null;
    if (showPreviewBanner) {
      banner = el("p", "aw-banner");
      banner.setAttribute("role", "note");
      panel.appendChild(banner);
    }

    // The conversation is re-rendered as a whole, so it is not a live region:
    // replies and errors are announced through the status element below.
    var log = el("div", "aw-log");
    log.tabIndex = 0;
    panel.appendChild(log);

    // Outside the panel: a hidden (display:none) panel would silence it.
    var status = el("p", "aw-sr");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");

    var composer = el("form", "aw-composer");
    composer.setAttribute("novalidate", "");
    var inputLabel = el("label", "aw-sr");
    var input = el("textarea", "aw-input");
    input.id = panelId + "-input";
    inputLabel.htmlFor = input.id;
    input.rows = 1;
    input.maxLength = MAX_MESSAGE_LENGTH;
    input.setAttribute("dir", "auto");
    input.setAttribute("autocomplete", "off");
    input.setAttribute("enterkeyhint", "send");
    var sendButton = el("button", "aw-send");
    sendButton.type = "submit";
    sendButton.disabled = true;
    sendButton.appendChild(sendIcon());
    composer.appendChild(inputLabel);
    composer.appendChild(input);
    composer.appendChild(sendButton);
    panel.appendChild(composer);

    wrapper.appendChild(panel);
    wrapper.appendChild(launcher);
    wrapper.appendChild(status);
    root.appendChild(wrapper);
    document.body.appendChild(host);

    var typingRow = null;

    launcher.addEventListener("click", function () {
      setOpen(!state.isOpen);
    });
    wrapper.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && state.isOpen) {
        event.stopPropagation();
        setOpen(false);
      }
    });
    input.addEventListener("input", function () {
      autoSize();
      updateSendButton();
    });
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        submit();
      }
    });
    composer.addEventListener("submit", function (event) {
      event.preventDefault();
      submit();
    });

    applyLanguage();
    exposeApi();
    // data-open only sets the first view of the tab session: once the visitor
    // has opened or closed the chat, their choice is kept on every page (a
    // full-screen panel on a phone must not come back on each page).
    var savedOpen = storageGet(sessionStorageOrNull(), storagePrefix + "open");
    if (savedOpen === "1" || (savedOpen === null && script.getAttribute("data-open") === "true")) {
      setOpen(true, true);
    }
    window.addEventListener("storage", function (event) {
      if (event.key === storagePrefix + "history" || event.key === storagePrefix + "cursor") {
        adoptStoredState();
      }
    });
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "hidden") {
        stopPolling();
      } else {
        schedulePoll(0);
      }
    });
    schedulePoll(0);

