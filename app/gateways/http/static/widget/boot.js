  var script = findOwnScript();
  if (!script) {
    return;
  }

  var businessId = (
    script.getAttribute(BUSINESS_ATTRIBUTE) ||
    script.getAttribute("data-business-id") ||
    ""
  ).trim();
  if (!businessId) {
    warn("the script tag needs a " + BUSINESS_ATTRIBUTE + " attribute.");
    return;
  }

  var loaded = (window.__assistantWorkshopChat = window.__assistantWorkshopChat || {});
  if (loaded[businessId]) {
    return;
  }
  loaded[businessId] = true;

  var apiBase = resolveApiBase(script);
  var configUrl = apiBase + CONFIG_PATH.replace("{business_id}", encodeURIComponent(businessId));
  var messagesUrl =
    apiBase + MESSAGES_PATH.replace("{business_id}", encodeURIComponent(businessId));
  var storagePrefix = STORAGE_PREFIX + businessId + ":";

  start();

  function start() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start, { once: true });
      return;
    }
    requestJson(configUrl, null).then(
      function (result) {
        var config = result.body;
        var isPreview = script.getAttribute("data-preview") === "true";
        if (!result.ok || !config || typeof config !== "object") {
          warn("the chat configuration could not be loaded (HTTP " + result.status + ").");
          return;
        }
        if (!config.is_enabled && !isPreview) {
          info("the chat is switched off for this business.");
          return;
        }
        mount(config, isPreview);
      },
      function () {
        warn("the chat configuration could not be loaded.");
      }
    );
  }

