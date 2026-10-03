    // `mayHaveArrived`: the request broke off (network, or the visitor left
    // the page): the API may have the message, so the stored copy stays and
    // the next page looks for its answer. A refused message (an HTTP error)
    // is kept on this page only, for Retry.
    function markFailed(item, message, detail, mayHaveArrived) {
      item.pending = false;
      item.failed = true;
      item.error = message;
      item.detail = detail;
      if (!mayHaveArrived) {
        saveHistory();
      }
      announce(message);
      renderLog();
    }

    // After a 429 the send button and Retry wait for the API's Retry-After,
    // then come back by themselves.
    function holdSending(waitMs) {
      var wait = waitMs > 0 ? waitMs : RATE_LIMIT_DEFAULT_WAIT_MS;
      state.sendHeldUntil = Date.now() + wait;
      window.setTimeout(function () {
        updateSendButton();
        renderLog();
      }, wait + 50);
    }

    function isSendingHeld() {
      return Date.now() < state.sendHeldUntil;
    }

    function waitAfter(result) {
      if (result.status !== 429) {
        return 0;
      }
      return result.retryAfterMs > 0 ? result.retryAfterMs : RATE_LIMIT_DEFAULT_WAIT_MS;
    }

    function errorTextFor(statusCode) {
      // 404: unknown business or chat switched off; 409: assistant not live.
      if (statusCode === 404 || statusCode === 409) {
        return text("unavailable");
      }
      if (statusCode === 429) {
        return text("rateLimited");
      }
      if (statusCode === 413) {
        return text("tooLong");
      }
      return text("failed");
    }

    // Owners previewing the widget (data-preview) also see the API's reason.
    function previewDetail(result) {
      var message = result.body && typeof result.body.message === "string" ? result.body.message : "";
      return isPreview ? message : "";
    }

    function renderLog() {
      var wasAtEnd = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
      while (log.firstChild) {
        log.removeChild(log.firstChild);
      }
      var greeting = configGreeting(config, state.language);
      log.appendChild(
        greeting
          ? messageRow("assistant", greeting.text, greeting.direction)
          : messageRow("assistant", text("greeting").split("{business}").join(config.business_name || ""))
      );
      state.history.forEach(function (item) {
        if (item.role === "notice") {
          var notice = el("p", "aw-notice");
          notice.textContent = text(item.key || "handedOff");
          log.appendChild(notice);
          return;
        }
        var row = messageRow(item.role, item.text, item.direction, item.role === "staff" ? text("staff") : "");
        if (item === state.pendingItem || (item.role === "visitor" && isAwaiting(item))) {
          row.className += " aw-pending";
        }
        log.appendChild(row);
        if (item.failed) {
          log.appendChild(errorRow(item));
        }
      });
      if (typingRow) {
        log.appendChild(typingRow);
      }
      renderActions();
      if (wasAtEnd || state.isSending) {
        scrollToEnd();
      }
    }

    function errorRow(item) {
      var row = el("div", "aw-error");
      row.setAttribute("role", "alert");
      var message = el("span", "aw-error-text");
      message.textContent = item.error || text("failed");
      if (item.detail) {
        var detail = el("span", "aw-error-detail");
        detail.setAttribute("dir", "auto");
        detail.textContent = item.detail;
        message.appendChild(detail);
      }
      var retry = el("button", "aw-retry");
      retry.type = "button";
      retry.textContent = text("retry");
      retry.disabled = state.isSending || isSendingHeld();
      retry.addEventListener("click", function () {
        if (!state.isSending && !isSendingHeld()) {
          send(item);
          input.focus();
        }
      });
      row.appendChild(message);
      row.appendChild(retry);
      return row;
    }

    function showTyping(isTyping) {
      if (isTyping) {
        typingRow = el("div", "aw-typing");
        typingRow.title = text("typing");
        typingRow.appendChild(el("span", ""));
        typingRow.appendChild(el("span", ""));
        typingRow.appendChild(el("span", ""));
        announce(text("typing"));
        log.appendChild(typingRow);
        scrollToEnd();
      } else if (typingRow) {
        if (typingRow.parentNode) {
          typingRow.parentNode.removeChild(typingRow);
        }
        typingRow = null;
      }
    }

    function updateSendButton() {
      sendButton.disabled = state.isSending || isSendingHeld() || input.value.trim() === "";
    }

    function autoSize() {
      input.style.height = "auto";
      input.style.height = Math.min(input.scrollHeight + 2, 132) + "px";
    }

    function scrollToEnd() {
      log.scrollTop = log.scrollHeight;
    }

    function announce(message) {
      status.textContent = "";
      window.setTimeout(function () {
        status.textContent = message;
      }, 50);
    }

    function saveHistory() {
      if (state.history.length > MAX_STORED_MESSAGES * 2) {
        state.history.splice(0, state.history.length - MAX_STORED_MESSAGES * 2);
      }
      var stored = state.history
        .filter(function (item) {
          return !item.failed;
        })
        .slice(-MAX_STORED_MESSAGES)
        .map(function (item) {
          return {
            role: item.role,
            id: item.id,
            text: item.text,
            direction: item.direction,
            key: item.key,
            pending: item.pending === true ? true : undefined,
            sentAt: item.pending === true ? item.sentAt : undefined
          };
        });
      // Remembered so this tab does not take its own write for another tab's.
      state.storedHistory = JSON.stringify(stored);
      storageSet(localStorageOrNull(), storagePrefix + "history", state.storedHistory);
    }

    function text(key) {
      return translate(state.language, key);
    }
  }

