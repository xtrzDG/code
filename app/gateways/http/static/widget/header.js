/*!
 * Assistant Workshop — website chat widget.
 *
 * Embed (the cabinet gives this snippet; GET /v1/businesses/{id}/channels/web/snippet):
 *   <script src="https://<api>/widget.js" data-tenant="<business id>" async></script>
 *
 * Optional attributes of the script tag (they win over the cabinet's choices):
 *   data-color="#ad5732"   accent colour (hex; default: the cabinet's colour)
 *   data-position="left"   launcher in the bottom-left corner (default: the
 *                          cabinet's corner, else right)
 *   data-language="ka"     interface language (default: the visitor's browser
 *                          language among the business languages)
 *   data-open="true"       open the chat panel on the first page of a visit
 *                          (once the visitor opens or closes it, that choice
 *                          is kept on the next pages)
 *   data-preview="true"    show the widget even while the chat is switched off
 *   data-api-base="https://<api>"   API origin (default: the script's origin)
 *   data-mode="page"       the chat fills a page instead of a corner (the
 *                          hosted chat page /c/{slug}): no launcher, always
 *                          open, the business's other channels on top
 *   data-container="<id>"  page mode: the element the chat fills (default:
 *                          the whole window)
 *
 * No dependencies and no cookies. The visitor is identified by a random
 * session key kept in localStorage; the widget renders inside a shadow root,
 * so the host page's styles and the widget's styles never mix.
 *
 * Sending a message is accepted at once (202): a worker answers it, and the
 * widget shows the assistant typing while it polls GET .../messages for the
 * answer, every second or so, until it arrives or staff take over. It also
 * polls for answers it has not shown: while a handoff to staff is open,
 * while the panel is open within 24 hours of the visitor's last exchange
 * (staff can write to any website chat), and after a page was left while
 * an answer was being written. Every few seconds at first, slower while
 * nothing new arrives, and not at all while the page is hidden. The
 * visitor key travels in a request header, never in the URL.
 * When the API says "too many messages" (429), sending and Retry wait for
 * its Retry-After, and polls slow down to it.
 * Tabs of one site share one history: each tab adopts what the others saved.
 * Before the first message the business's top questions are one tap away;
 * "Talk to a person" passes the conversation to staff (POST .../handoff),
 * "New conversation" starts over under a new visitor key, and the footer
 * says it is an AI assistant that can make mistakes, with the privacy notice.
 * window.AssistantWorkshopChat.open() / .close() / .toggle() control it.
 */
(function () {
  "use strict";

  // Kept in sync with the API by tests/channels/test_widget_script.py.
  var BUSINESS_ATTRIBUTE = "data-tenant";
  var CONFIG_PATH = "/v1/widget/{business_id}/config";
  var MESSAGES_PATH = "/v1/widget/{business_id}/messages";
  var HANDOFF_PATH = "/v1/widget/{business_id}/handoff";
  var ERRORS_PATH = "/v1/widget/errors";
  var SCRIPT_FILE_NAME = "/widget.js";

  var MAX_MESSAGE_LENGTH = 4000;
  var MAX_STORED_MESSAGES = 60;
  var REQUEST_TIMEOUT_MS = 90000;
  var SESSION_KEY_PATTERN = /^[A-Za-z0-9_-]{16,128}$/;
  var SESSION_KEY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
  var COLOR_PATTERN = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;
  var DEFAULT_ACCENT = "#ad5732";
  var STORAGE_PREFIX = "aw-chat:";
  var RTL_LANGUAGES = ["ar", "he", "fa", "ur", "yi", "ps", "sd", "ug", "ckb", "dv"];
  var URL_PATTERN = /\bhttps?:\/\/[^\s<>"']+/g;
  // Hebrew, Arabic, Syriac, Thaana, NKo and their presentation forms.
  var RTL_CHARACTER_PATTERN = /[\u0590-\u08FF\uFB1D-\uFDFF\uFE70-\uFEFC]/;
  var SESSION_KEY_HEADER = "X-Widget-Session-Key";
  var POSITIONS = ["left", "right"];
  var PAGE_MODE = "page";
  var WEB_LINK_PATTERN = /^https?:\/\/[^\s]+$/;
  var CONTACT_LINK_PATTERN = /^(?:https:\/\/[^\s]+|tel:\+[0-9]{7,15})$/;
  var CONTACT_NAMES = {
    whatsapp: "WhatsApp",
    telegram: "Telegram",
    messenger: "Messenger",
    instagram: "Instagram"
  };
  var MAX_STARTERS = 3;
  // Polling for staff replies: fast after activity, slower while idle.
  var POLL_FIRST_DELAY_MS = 4000;
  var POLL_BACKOFF_FACTOR = 1.6;
  var POLL_MAX_DELAY_OPEN_MS = 30000;
  var POLL_MAX_DELAY_CLOSED_MS = 60000;
  var POLL_MORE_DELAY_MS = 500;
  // Waiting for the answer to an accepted message (202): a worker writes it
  // within seconds, so poll often, a little slower each time.
  var POLL_AWAIT_DELAY_MS = 1000;
  var POLL_AWAIT_MAX_DELAY_MS = 3000;
  var POLL_AWAIT_BACKOFF_FACTOR = 1.25;
  // A handoff or an exchange in the last 24 hours keeps an open panel
  // polling: staff can write to any website chat.
  var HANDOFF_MEMORY_MS = 24 * 60 * 60 * 1000;
  // A 429 without a readable Retry-After waits this long; a longer one is
  // capped (the API asks for at most a minute).
  var RATE_LIMIT_DEFAULT_WAIT_MS = 10000;
  var RATE_LIMIT_MAX_WAIT_MS = 10 * 60 * 1000;
  var SVG_NS = "http://www.w3.org/2000/svg";
  // The error beacon: a few reports per page at most, error type names only.
  var MAX_ERROR_REPORTS = 3;
  var ERROR_NAME_PATTERN = /^[A-Za-z_$][A-Za-z0-9_$]{0,63}$/;
  var BUSINESS_ID_PATTERN = /^business_[0-9a-f-]{36}$/;
  var WIDGET_FRAME_PATTERN = /widget\.js(?:\?[^\s:)]*)?:(\d+):(\d+)/;
  // Fallback when the browser blocks localStorage / sessionStorage.
  var memoryStorage = {};

