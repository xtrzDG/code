    // --- the live stream: typing and answers the moment they are ready ----

    // A ticket from an answer of the API (a message's 202, a poll): the
    // visitor's stream opens with it while the widget listens.
    function receiveTicket(ticket) {
      if (typeof ticket !== "string" || !STREAM_TICKET_PATTERN.test(ticket)) {
        return;
      }
      state.streamTicket = ticket;
      syncStream();
    }

    // The stream is open exactly while the widget listens for answers (see
    // shouldPoll), on a visible page, with EventSource; polling stays the
    // fallback everywhere else.
    function syncStream() {
      var isWanted =
        typeof window.EventSource === "function" &&
        !isLivePreview &&
        state.streamTicket !== null &&
        !state.pollStopped &&
        document.visibilityState !== "hidden" &&
        Date.now() >= state.streamRetryAt &&
        (state.isSending || shouldPoll());
      if (isWanted && !state.stream) {
        openStream();
      } else if (!isWanted && state.stream) {
        closeStream();
      }
    }

    function openStream() {
      var source;
      try {
        source = new window.EventSource(
          eventsUrl + "?ticket=" + encodeURIComponent(state.streamTicket)
        );
      } catch (error) {
        state.streamTicket = null;
        return;
      }
      state.stream = source;
      var whileCurrent = function (handle) {
        return guarded("poll", function (event) {
          if (state.stream === source) {
            handle(event);
          }
        });
      };
      // Up (again): poll once for what came before the stream heard it.
      source.addEventListener("stream.ready", whileCurrent(function () {
        state.isStreamLive = true;
        catchUp();
      }));
      source.addEventListener("typing_started", whileCurrent(function () {
        state.workerTyping = true;
        syncTyping();
      }));
      source.addEventListener("answer_ready", whileCurrent(function (event) {
        receiveAnswerEvent(event.data);
      }));
      source.addEventListener("stream.resync", whileCurrent(catchUp));
      source.onerror = whileCurrent(function () {
        // Reconnecting by itself, or refused for good (an expired ticket,
        // too many streams): poll as before meanwhile, dots drawn here.
        state.isStreamLive = false;
        state.typingGated = false;
        if (source.readyState === STREAM_CLOSED) {
          closeStream();
          state.streamTicket = null;
          state.streamRetryAt = Date.now() + STREAM_RETRY_PAUSE_MS;
        }
        state.pollDelay = POLL_AWAIT_DELAY_MS;
        schedulePoll(POLL_AWAIT_DELAY_MS);
      });
    }

    function closeStream() {
      if (state.stream) {
        state.stream.close();
      }
      state.stream = null;
      state.isStreamLive = false;
      state.typingGated = false;
    }

    // An answer is stored: show its text at once when the stream carried
    // it (a model reply the guard passed), as a draft the next poll
    // replaces with the stored text; poll for the rest (staff messages,
    // a booking's confirmation, a reply the guard changed).
    function receiveAnswerEvent(raw) {
      var answer = null;
      try {
        answer = JSON.parse(raw);
      } catch (error) {
        answer = null;
      }
      var isDraft =
        answer &&
        typeof answer.message_id === "string" &&
        typeof answer.text === "string" &&
        answer.text !== "" &&
        !isKnownMessage(answer.message_id);
      if (isDraft) {
        state.history.push({
          role: answer.author === "staff" ? "staff" : "assistant",
          id: answer.message_id,
          text: answer.text,
          direction: answer.direction === "rtl" ? "rtl" : "ltr",
          draft: true
        });
        clearPending();
        markActivity();
        saveHistory();
        renderLog();
        noteReply(answer.text);
      }
      catchUp();
    }

    function isKnownMessage(messageId) {
      return state.history.some(function (item) {
        return item.id === messageId;
      });
    }

    // One poll now, or right after the one running.
    function catchUp() {
      if (state.isPolling || state.isSending) {
        state.catchUpPending = true;
        return;
      }
      poll(true);
    }

    // --- no answer: tell the visitor, pass the chat to staff ---------------

    function lastVisitorItem() {
      for (var index = state.history.length - 1; index >= 0; index -= 1) {
        if (state.history[index].role === "visitor") {
          return state.history[index];
        }
      }
      return null;
    }

    // At the deadline of the visitor's waiting message, poll once more;
    // the poll gives up on it when the answer is still missing.
    function armNoAnswerTimer() {
      if (state.noAnswerTimer !== null) {
        window.clearTimeout(state.noAnswerTimer);
        state.noAnswerTimer = null;
      }
      var item = lastVisitorItem();
      if (!item || item.pending !== true || isLivePreview) {
        return;
      }
      var wait = Math.max(0, (item.sentAt || 0) + NO_ANSWER_AFTER_MS - Date.now());
      state.noAnswerTimer = window.setTimeout(
        guarded("poll", function () {
          state.noAnswerTimer = null;
          catchUp();
        }),
        wait + 50
      );
    }

    function checkNoAnswer() {
      var item = lastVisitorItem();
      if (
        item &&
        item.pending === true &&
        !state.isHandedOff &&
        !state.isSending &&
        Date.now() - (item.sentAt || 0) >= NO_ANSWER_AFTER_MS
      ) {
        giveUpWaiting(item);
      }
    }

    // "We'll answer as soon as we can" instead of dots that just vanish, and
    // the conversation goes to staff (who see why); the stored notice is
    // known by id, so polling never shows it twice.
    function giveUpWaiting(item) {
      item.pending = false;
      state.workerTyping = false;
      var notice = { role: "notice", key: "noAnswer" };
      state.history.push(notice);
      state.handoffNoticeShown = true;
      announce(text("noAnswer"));
      markActivity();
      saveHistory();
      syncTyping();
      renderLog();
      requestJson(
        handoffUrl,
        withVisitSource({
          session_key: state.sessionKey,
          language: state.language,
          reason: "no_answer"
        })
      ).then(
        guarded("poll", function (result) {
          if (!result.ok || !result.body) {
            return;
          }
          if (typeof result.body.message_id === "string") {
            notice.id = result.body.message_id;
            if (!state.cursor) {
              saveCursor(notice.id);
            }
          }
          setHandedOff(true);
          saveHistory();
          renderLog();
          state.pollDelay = POLL_FIRST_DELAY_MS;
          schedulePoll(POLL_FIRST_DELAY_MS);
        }),
        function () {
          return null;
        }
      );
    }

