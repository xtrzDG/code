    function applyLanguage() {
      var direction = languageDirection(config, state.language);
      wrapper.setAttribute("dir", direction);
      wrapper.setAttribute("lang", state.language);
      updateLauncherLabel();
      panel.setAttribute("aria-label", config.business_name || text("subtitle"));
      log.setAttribute("aria-label", config.business_name || text("subtitle"));
      subtitle.textContent = text("subtitle");
      closeButton.setAttribute("aria-label", text("close"));
      closeButton.title = text("close");
      if (languageSelect) {
        languageSelect.setAttribute("aria-label", text("language"));
      }
      if (banner) {
        banner.textContent = text("preview");
      }
      input.placeholder = text("placeholder");
      inputLabel.textContent = text("placeholder");
      sendButton.setAttribute("aria-label", text("send"));
      sendButton.title = text("send");
      applyChromeLanguage();
      renderLog();
    }

    function setOpen(isOpen, keepFocus) {
      if (isPageMode && !isOpen) {
        // A chat page has nothing to close to.
        return;
      }
      state.isOpen = isOpen;
      panel.hidden = !isOpen;
      launcher.setAttribute("aria-expanded", isOpen ? "true" : "false");
      if (isOpen) {
        wrapper.classList.remove("aw-unread");
      }
      updateLauncherLabel();
      launcher.replaceChild(isOpen ? closeIcon() : chatIcon(), launcher.firstChild);
      wrapper.classList.toggle("aw-open", isOpen);
      storageSet(sessionStorageOrNull(), storagePrefix + "open", isOpen ? "1" : "0");
      if (isOpen) {
        scrollToEnd();
        if (!keepFocus) {
          input.focus();
        }
        state.pollDelay = POLL_FIRST_DELAY_MS;
        schedulePoll(0);
      } else if (!keepFocus) {
        launcher.focus();
      }
    }

    // The launcher's name also tells a screen reader about an unread reply.
    function updateLauncherLabel() {
      var label = text(state.isOpen ? "close" : "open");
      if (!state.isOpen && wrapper.classList.contains("aw-unread")) {
        label += " (" + text("newReply") + ")";
      }
      launcher.setAttribute("aria-label", label);
      launcher.title = label;
    }

    // A reply arrived: read it out when the panel is open, else mark the
    // launcher unread and say that a reply came.
    function noteReply(replyText) {
      if (state.isOpen) {
        announce(replyText);
        return;
      }
      wrapper.classList.add("aw-unread");
      updateLauncherLabel();
      announce(text("newReply"));
    }

    function exposeApi() {
      window.AssistantWorkshopChat = {
        open: function () {
          setOpen(true);
        },
        close: function () {
          setOpen(false);
        },
        toggle: function () {
          setOpen(!state.isOpen);
        }
      };
    }

    function submit() {
      var messageText = input.value.trim();
      if (!messageText || state.isSending) {
        return;
      }
      if (isSendingHeld()) {
        announce(text("rateLimited"));
        return;
      }
      if (messageText.length > MAX_MESSAGE_LENGTH) {
        announce(text("tooLong"));
        return;
      }
      input.value = "";
      autoSize();
      adoptStoredState();
      var item = { role: "visitor", text: messageText, failed: false };
      state.history.push(item);
      send(item);
    }

    function send(item) {
      stopPolling();
      state.isSending = true;
      state.pendingItem = item;
      item.failed = false;
      item.error = "";
      // Stored before sending: if the visitor leaves while the answer is
      // being written, the next page shows the question and fetches it.
      item.pending = true;
      item.sentAt = Date.now();
      saveHistory();
      updateSendButton();
      renderLog();
      showTyping(true);
      requestJson(messagesUrl, {
        session_key: state.sessionKey,
        text: item.text
      }).then(
        guarded("send", function (result) {
          state.isSending = false;
          state.pendingItem = null;
          if (result.status === 202) {
            awaitAnswer(item);
            return;
          }
          showTyping(false);
          if (result.ok && result.body) {
            receiveReply(result.body);
          } else {
            if (result.status === 429) {
              holdSending(result.retryAfterMs);
            }
            markFailed(item, errorTextFor(result.status), previewDetail(result));
          }
          updateSendButton();
          state.pollDelay = POLL_FIRST_DELAY_MS;
          if (result.ok) {
            // Catch up once: the answer again (skipped by id) and any staff
            // message written while the assistant was answering.
            poll(true);
          } else {
            schedulePoll(Math.max(POLL_FIRST_DELAY_MS, waitAfter(result)));
          }
        }),
        function () {
          showTyping(false);
          state.isSending = false;
          state.pendingItem = null;
          markFailed(item, text("failed"), "", true);
          updateSendButton();
          schedulePoll(POLL_FIRST_DELAY_MS);
        }
      );
    }

    // The API accepted the message (202) and a worker is answering it: the
    // typing dots stay and polling brings the answer (mount_polling).
    function awaitAnswer(item) {
      item.pending = true;
      item.sentAt = Date.now();
      markActivity();
      saveHistory();
      updateSendButton();
      renderLog();
      state.pollDelay = POLL_AWAIT_DELAY_MS;
      schedulePoll(POLL_AWAIT_DELAY_MS);
    }

    // An answer in the response itself (200): an API instance of an older
    // release during a deploy still answers in the request.
    function receiveReply(reply) {
      clearPending();
      if (typeof reply.text === "string" && reply.text) {
        state.history.push({
          role: "assistant",
          id: typeof reply.message_id === "string" ? reply.message_id : undefined,
          text: reply.text,
          direction: reply.direction === "rtl" ? "rtl" : "ltr"
        });
        noteReply(reply.text);
      } else if (reply.is_handed_off) {
        noteHandoff();
      }
      // The position only moves forward by polling (right after this reply),
      // so staff messages written meanwhile are never skipped.
      if (!state.cursor && typeof reply.cursor === "string" && reply.cursor) {
        saveCursor(reply.cursor);
      }
      setHandedOff(reply.is_handed_off === true);
      markActivity();
      saveHistory();
      renderLog();
    }

    // Staff took the conversation over: say so once.
    function noteHandoff() {
      if (state.handoffNoticeShown) {
        return;
      }
      state.handoffNoticeShown = true;
      state.history.push({ role: "notice", key: "handedOff" });
      announce(text("handedOff"));
    }
