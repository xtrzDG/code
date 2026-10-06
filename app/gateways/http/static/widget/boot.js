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
  var handoffUrl =
    apiBase + HANDOFF_PATH.replace("{business_id}", encodeURIComponent(businessId));
  var eventsUrl =
    apiBase + EVENTS_PATH.replace("{business_id}", encodeURIComponent(businessId));
  var isPageMode = script.getAttribute("data-mode") === PAGE_MODE;
  // The cabinet's preview: shown even while switched off, sends nothing,
  // keeps nothing in the browser and follows the owner's choices.
  var isLivePreview = script.getAttribute("data-preview") === LIVE_PREVIEW;
  var storagePrefix = STORAGE_PREFIX + businessId + ":";
  // Where the visitor came from (the business's reports group by it).
  var visitSource = loadVisitSource();

  start();

  function start() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start, { once: true });
      return;
    }
    requestJson(configUrl, null).then(
      guarded("boot", function (result) {
        var config = result.body;
        var isPreview = script.getAttribute("data-preview") === "true" || isLivePreview;
        if (!result.ok || !config || typeof config !== "object") {
          if (result.status >= 500) {
            reportWidgetError("config_failed", "boot", null, result.status);
          }
          warn("the chat configuration could not be loaded (HTTP " + result.status + ").");
          return;
        }
        if (!config.is_enabled && !isPreview) {
          info("the chat is switched off for this business.");
          return;
        }
        guarded("mount", mount)(config, isPreview);
      }),
      function () {
        warn("the chat configuration could not be loaded.");
      }
    );
  }

