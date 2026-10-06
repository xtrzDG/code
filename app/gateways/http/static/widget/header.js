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
 *   data-preview="live"    the cabinet's live preview (the hosted chat page
 *                          framed by the Channels page): like "true", and
 *                          nothing is sent or kept; the framing page of the
 *                          same origin may change the colour, corner and
 *                          language on the fly (window.postMessage)
 *   data-api-base="https://<api>"   API origin (default: the script's origin)
 *   data-mode="page"       the chat fills a page instead of a corner (the
 *                          hosted chat page /c/{slug}): no launcher, always
 *                          open, the business's other channels on top
 *   data-container="<id>"  page mode: the element the chat fills (default:
 *                          the whole window)
 *   data-theme="dark"      light or dark colours (default: the visitor's
 *                          system setting, prefers-color-scheme)
 *   data-source="qr"       where visitors of this page came from (default:
 *                          the page's ?src= or ?utm_source=); the business's
 *                          reports count conversations, bookings and value
 *                          per source
 *
 * No dependencies and no cookies. The visitor is identified by a random
 * session key kept in localStorage; the widget renders inside a shadow root,
 * so the host page's styles and the widget's styles never mix.
 *
 * Sending a message is accepted at once (202) with a ticket to the
 * visitor's live stream (GET .../events?ticket=..., EventSource): the
 * stream says when a worker starts writing the answer (the typing dots
 * show then) and when the answer is ready, with its text when the reply
 * guard passed it; the widget shows that draft at once and replaces it
 * with the stored text when it polls GET .../messages right after. The
 * visitor key never travels in an address: the ticket stands for it.
 * Without EventSource, or while the stream is down, the widget polls for
 * the answer every second or so, and draws the typing dots itself. It
 * also polls (slowly with a live stream) for answers it has not shown:
 * while a handoff to staff is open, while the panel is open within 24
 * hours of the visitor's last exchange (staff can write to any website
 * chat), and after a page was left while an answer was being written;
 * not at all while the page is hidden. The visitor key travels in a
 * request header, never in the URL. When no answer comes for 90 seconds
 * (no worker took the message), the visitor reads "We'll answer as soon
 * as we can" and the conversation goes to staff (POST .../handoff with
 * the reason no_answer) instead of the dots just disappearing.
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
  var EVENTS_PATH = "/v1/widget/{business_id}/events";
  var ERRORS_PATH = "/v1/widget/errors";
  var SCRIPT_FILE_NAME = "/widget.js";

  var MAX_MESSAGE_LENGTH = 4000;
  var MAX_STORED_MESSAGES = 60;
  var MAX_SOURCE_LENGTH = 200;
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
  var THEMES = ["light", "dark"];
  var STREAM_TICKET_PATTERN = /^[A-Za-z0-9_-]{40,120}$/;
  // With the live stream up, polls are only a safety net.
  var STREAM_SAFETY_POLL_MS = 15000;
  // A stream the API refused (an expired ticket, too many streams) is tried
  // again after this pause, with the ticket of a later answer.
  var STREAM_RETRY_PAUSE_MS = 30000;
  // EventSource.CLOSED: the browser will not reconnect by itself.
  var STREAM_CLOSED = 2;
  // No answer this long after a message: tell the visitor and pass the
  // conversation to staff.
  var NO_ANSWER_AFTER_MS = 90000;
  var PAGE_MODE = "page";
  var LIVE_PREVIEW = "live";
  // Messages between the live preview and the Channels page that frames it.
  var PREVIEW_LOOK_MESSAGE = "assistant-workshop:preview-look";
  var PREVIEW_READY_MESSAGE = "assistant-workshop:preview-ready";
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

