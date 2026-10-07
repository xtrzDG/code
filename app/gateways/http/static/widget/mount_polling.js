    // --- answers the widget has not shown yet -----------------------------

    function shouldPoll() {
      if (state.pollStopped || document.visibilityState === "hidden") {
        return false;
      }
      if (state.isHandedOff) {
        return true;
      }
      if (awaitingAnswer() && !state.isSending) {
        return true;
      }
      var lastAt = Math.max(state.handoffAt, state.activityAt);
      return state.isOpen && lastAt > 0 && Date.now() - lastAt < HANDOFF_MEMORY_MS;
    }

    // The visitor's last message was sent (maybe from a page since left) and
    // its answer has not been shown yet.
    function awaitingAnswer() {
      for (var index = state.history.length - 1; index >= 0; index -= 1) {
        var item = state.history[index];
        if (item.role === "visitor") {
          return isAwaiting(item);
        }
      }
      return false;
    }

    function isAwaiting(item) {
      return item.pending === true && Date.now() - (item.sentAt || 0) < REQUEST_TIMEOUT_MS;
    }

    function clearPending() {
      state.history.forEach(function (item) {
        if (item.role === "visitor") {
          item.pending = false;
        }
      });
    }

    function markActivity() {
      state.activityAt = Date.now();
      storageSet(localStorageOrNull(), storagePrefix + "activity-at", String(state.activityAt));
    }

    // The history and position another tab saved; this tab's unsent and
    // failed messages stay at the end.
    function adoptStoredState() {
      if (state.isSending) {
        // Adopted after the answer: the message being sent is in the history.
        return;
      }
      var raw = storageGet(localStorageOrNull(), storagePrefix + "history");
      if (raw !== state.storedHistory) {
        var unsaved = state.history.filter(function (item) {
          return item.failed;
        });
        state.history = loadHistory().concat(unsaved);
        state.storedHistory = raw;
        state.handoffNoticeShown = state.history.some(function (item) {
          return item.role === "notice";
        });
        renderLog();
      }
      var cursor = storageGet(localStorageOrNull(), storagePrefix + "cursor");
      if (cursor) {
        state.cursor = cursor;
      }
      state.activityAt = Math.max(
        state.activityAt,
        Number(storageGet(localStorageOrNull(), storagePrefix + "activity-at")) || 0
      );
    }

    // The typing dots show while the answer to a message is being written
    // (not once staff took over: the assistant stays silent then). With a
    // live stream they wait for the worker's own signal (typing_started);
    // without one they show from the moment the message is sent.
    function syncTyping() {
      var isTyping =
        (state.isSending && !state.typingGated) ||
        (awaitingAnswer() &&
          !state.isHandedOff &&
          (!state.typingGated || state.workerTyping));
      if (isTyping !== (typingRow !== null)) {
        showTyping(isTyping);
      }
    }

    function schedulePoll(delay) {
      stopPolling();
      syncTyping();
      syncStream();
      if (!shouldPoll() || state.isSending) {
        return;
      }
      state.pollTimer = window.setTimeout(
        guarded("poll", function () {
          poll(false);
        }),
        delay
      );
    }

    function stopPolling() {
      if (state.pollTimer !== null) {
        window.clearTimeout(state.pollTimer);
        state.pollTimer = null;
      }
    }

    function nextDelay() {
      if (state.isStreamLive) {
        // The stream brings answers; a slow poll is only the safety net.
        state.pollDelay = Math.max(state.pollDelay, STREAM_SAFETY_POLL_MS);
        return state.pollDelay;
      }
      if (awaitingAnswer() && !state.isHandedOff) {
        var awaitDelay = Math.max(state.pollDelay, POLL_AWAIT_DELAY_MS) * POLL_AWAIT_BACKOFF_FACTOR;
        state.pollDelay = Math.min(Math.round(awaitDelay), POLL_AWAIT_MAX_DELAY_MS);
        return state.pollDelay;
      }
      var limit = state.isOpen ? POLL_MAX_DELAY_OPEN_MS : POLL_MAX_DELAY_CLOSED_MS;
      state.pollDelay = Math.min(Math.round(state.pollDelay * POLL_BACKOFF_FACTOR), limit);
      return state.pollDelay;
    }

    function poll(isCatchUp) {
      state.pollTimer = null;
      if (state.isPolling || state.isSending || state.pollStopped) {
        return;
      }
      if (isCatchUp !== true && !shouldPoll()) {
        return;
      }
      // Start from the shared position, so another tab's answers are not
      // appended out of order.
      adoptStoredState();
      state.isPolling = true;
      var url = messagesUrl;
      var hadCursor = Boolean(state.cursor);
      if (hadCursor) {
        url += "?after=" + encodeURIComponent(state.cursor);
      }
      requestJson(url, null, state.sessionKey).then(
        guarded("poll", function (result) {
          state.isPolling = false;
          if (result.status === 404) {
            // The chat was switched off: stop asking.
            state.pollStopped = true;
            closeStream();
            return;
          }
          if (!result.ok || !result.body || !Array.isArray(result.body.items)) {
            afterPoll();
            schedulePoll(Math.max(nextDelay(), waitAfter(result)));
            return;
          }
          var added = receiveMessages(result.body);
          receiveTicket(result.body.stream_ticket);
          afterPoll();
          if (result.body.has_more === true || (!hadCursor && state.cursor && awaitingAnswer())) {
            // More to read, or the first position of a new visitor: the
            // answer comes right after it.
            schedulePoll(POLL_MORE_DELAY_MS);
          } else if (added > 0) {
            state.pollDelay = POLL_FIRST_DELAY_MS;
            schedulePoll(POLL_FIRST_DELAY_MS);
          } else {
            schedulePoll(nextDelay());
          }
        }),
        function () {
          state.isPolling = false;
          afterPoll();
          schedulePoll(nextDelay());
        }
      );
    }

    // After every poll: give up on an answer past its deadline, and run the
    // catch-up the stream asked for meanwhile.
    function afterPoll() {
      checkNoAnswer();
      if (state.catchUpPending) {
        state.catchUpPending = false;
        window.setTimeout(guarded("poll", catchUp), 0);
      }
    }

    function receiveMessages(page) {
      var known = {};
      state.history.forEach(function (item) {
        if (item.id) {
          known[item.id] = item;
        }
      });
      var added = 0;
      var replaced = 0;
      var lastText = "";
      page.items.forEach(function (message) {
        if (!message || typeof message.id !== "string" || typeof message.text !== "string") {
          return;
        }
        if (known[message.id] && known[message.id].draft) {
          // The stored text replaces the stream's draft.
          known[message.id].text = message.text;
          known[message.id].choices = readChoices(message.choices);
          delete known[message.id].draft;
          replaced += 1;
          return;
        }
        if (known[message.id] || !message.text) {
          return;
        }
        known[message.id] = true;
        state.history.push({
          role: message.author === "staff" ? "staff" : "assistant",
          id: message.id,
          text: message.text,
          direction: message.direction === "rtl" ? "rtl" : "ltr",
          choices: readChoices(message.choices)
        });
        lastText = message.text;
        added += 1;
      });
      if (typeof page.cursor === "string" && page.cursor) {
        saveCursor(page.cursor);
      }
      setHandedOff(page.is_handed_off === true);
      if (state.isHandedOff && awaitingAnswer()) {
        // Staff handle the conversation: they answer, not the assistant.
        clearPending();
        noteHandoff();
        saveHistory();
        renderLog();
      }
      if (added > 0) {
        clearPending();
        markActivity();
        saveHistory();
        renderLog();
        noteReply(lastText);
      } else if (replaced > 0) {
        saveHistory();
        renderLog();
      }
      return added;
    }

    function saveCursor(cursor) {
      state.cursor = cursor;
      storageSet(localStorageOrNull(), storagePrefix + "cursor", cursor);
    }

    function setHandedOff(isHandedOff) {
      state.isHandedOff = isHandedOff;
      storageSet(localStorageOrNull(), storagePrefix + "handoff", isHandedOff ? "1" : "0");
      if (isHandedOff) {
        state.handoffAt = Date.now();
        storageSet(localStorageOrNull(), storagePrefix + "handoff-at", String(state.handoffAt));
      }
    }

