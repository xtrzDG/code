
  // --- error beacon ------------------------------------------------------

  // Errors of the widget's own code go to POST /v1/widget/errors: what
  // failed and where in widget.js, never the message (it may quote the page
  // or what the visitor typed). At most a few per page, each once; the host
  // page's own errors are never reported.
  var reportedErrorKeys = {};
  var reportedErrorCount = 0;

  // `task` as a callback that reports what it throws instead of breaking
  // the host page (the widget keeps working where it can).
  function guarded(phase, task) {
    return function () {
      try {
        return task.apply(this, arguments);
      } catch (error) {
        reportWidgetError("script_error", phase, error, 0);
        warn("something went wrong in the chat; it was reported.");
        return undefined;
      }
    };
  }

  function reportWidgetError(kind, phase, error, statusCode) {
    try {
      var name = readErrorName(error);
      var position = readErrorPosition(error);
      var key = [kind, phase, name, position.line, statusCode].join(":");
      if (reportedErrorCount >= MAX_ERROR_REPORTS || reportedErrorKeys[key]) {
        return;
      }
      reportedErrorKeys[key] = true;
      reportedErrorCount += 1;
      var report = { kind: kind, phase: phase };
      if (BUSINESS_ID_PATTERN.test(businessId)) {
        report.business_id = businessId;
      }
      if (name) {
        report.error_name = name;
      }
      if (position.line !== null) {
        report.line = position.line;
        report.column = position.column;
      }
      if (statusCode >= 100 && statusCode <= 599) {
        report.status_code = statusCode;
      }
      sendErrorReport(apiBase + ERRORS_PATH, JSON.stringify(report));
    } catch (ignored) {
      // Reporting must never break the page.
    }
  }

  function sendErrorReport(url, body) {
    // text/plain keeps it a simple request: no preflight, no cookies.
    var type = "text/plain;charset=UTF-8";
    if (
      navigator.sendBeacon &&
      typeof Blob === "function" &&
      navigator.sendBeacon(url, new Blob([body], { type: type }))
    ) {
      return;
    }
    if (typeof window.fetch === "function") {
      window
        .fetch(url, {
          method: "POST",
          mode: "cors",
          credentials: "omit",
          keepalive: true,
          headers: { "Content-Type": type },
          body: body
        })
        .catch(function () {
          return null;
        });
    }
  }

  function readErrorName(error) {
    var name = error && typeof error.name === "string" ? error.name : "";
    return ERROR_NAME_PATTERN.test(name) ? name : "";
  }

  // Line and column of the first widget.js frame of the stack.
  function readErrorPosition(error) {
    var stack = error && typeof error.stack === "string" ? error.stack : "";
    var match = WIDGET_FRAME_PATTERN.exec(stack);
    if (!match) {
      return { line: null, column: null };
    }
    return { line: Number(match[1]), column: Number(match[2]) };
  }
