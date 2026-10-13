  // --- network -----------------------------------------------------------

  function requestJson(url, body, sessionKey) {
    var options = {
      method: body ? "POST" : "GET",
      credentials: "omit",
      mode: "cors",
      cache: "no-store",
      referrerPolicy: "strict-origin-when-cross-origin"
    };
    if (body) {
      // text/plain keeps this a simple request (no CORS preflight); the API
      // reads the body as JSON whatever its content type.
      options.headers = { "Content-Type": "text/plain;charset=UTF-8" };
      options.body = JSON.stringify(body);
    } else if (sessionKey) {
      // In a header, so access logs and proxies never record the key.
      options.headers = {};
      options.headers[SESSION_KEY_HEADER] = sessionKey;
    }
    return fetchJson(url, options);
  }

  // One photo or voice message for the visitor's next message, as the
  // multipart part "file"; the visitor key goes in a header (a preflighted
  // request: the API answers OPTIONS for it).
  function requestUpload(url, file, fileName, sessionKey) {
    var form = new FormData();
    form.append("file", file, fileName);
    var headers = {};
    headers[SESSION_KEY_HEADER] = sessionKey;
    return fetchJson(url, {
      method: "POST",
      credentials: "omit",
      mode: "cors",
      cache: "no-store",
      referrerPolicy: "strict-origin-when-cross-origin",
      headers: headers,
      body: form
    });
  }

  // The response's status, JSON body (null when there is none) and
  // Retry-After; a request that takes too long is aborted.
  function fetchJson(url, options) {
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = controller
      ? window.setTimeout(function () {
          controller.abort();
        }, REQUEST_TIMEOUT_MS)
      : null;
    if (controller) {
      options.signal = controller.signal;
    }
    return window.fetch(url, options).then(
      function (response) {
        if (timer) {
          window.clearTimeout(timer);
        }
        return response.text().then(function (raw) {
          var parsed = null;
          try {
            parsed = raw ? JSON.parse(raw) : null;
          } catch (error) {
            parsed = null;
          }
          return {
            ok: response.ok,
            status: response.status,
            body: parsed,
            retryAfterMs: readRetryAfterMs(response)
          };
        });
      },
      function (error) {
        if (timer) {
          window.clearTimeout(timer);
        }
        throw error;
      }
    );
  }

  // Retry-After of a 429 in milliseconds (the API exposes the header to
  // other sites); 0 when absent or not a number of seconds.
  function readRetryAfterMs(response) {
    var raw = response.headers && typeof response.headers.get === "function"
      ? response.headers.get("Retry-After")
      : null;
    if (!raw || !/^\s*\d+\s*$/.test(raw)) {
      return 0;
    }
    return Math.min(Number(raw) * 1000, RATE_LIMIT_MAX_WAIT_MS);
  }

