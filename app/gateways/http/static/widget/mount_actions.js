    // --- starter questions, "Talk to a person", "New conversation" ---------

    function buildContacts() {
      var links = (Array.isArray(config.contact_links) ? config.contact_links : []).filter(
        function (link) {
          return link && typeof link.url === "string" && CONTACT_LINK_PATTERN.test(link.url);
        }
      );
      if (!links.length) {
        return null;
      }
      var row = el("nav", "aw-contacts");
      var items = links.map(function (link) {
        var anchor = el("a", "aw-contact");
        anchor.href = link.url;
        if (link.url.indexOf("tel:") !== 0) {
          anchor.target = "_blank";
          anchor.rel = "noopener noreferrer";
        }
        anchor.appendChild(link.kind === "phone" ? phoneIcon() : chatIcon());
        var name = el("span", "");
        anchor.appendChild(name);
        row.appendChild(anchor);
        return { kind: link.kind, name: name };
      });
      return { row: row, items: items };
    }

    function buildConfirm() {
      var row = el("div", "aw-confirm");
      row.setAttribute("role", "group");
      row.hidden = true;
      var question = el("p", "aw-confirm-text");
      var yes = el("button", "aw-confirm-yes");
      yes.type = "button";
      yes.addEventListener("click", guarded("restart", restartConversation));
      var no = el("button", "aw-confirm-no");
      no.type = "button";
      no.addEventListener("click", function () {
        setConfirmingRestart(false);
        restartButton.focus();
      });
      row.appendChild(question);
      row.appendChild(yes);
      row.appendChild(no);
      return { row: row, question: question, yes: yes, no: no };
    }

    function buildStarters() {
      var row = el("div", "aw-starters");
      row.setAttribute("role", "group");
      row.hidden = true;
      return { row: row };
    }

    function buildActions() {
      var row = el("div", "aw-actions");
      var person = el("button", "aw-person");
      person.type = "button";
      person.appendChild(personIcon());
      var label = el("span", "");
      person.appendChild(label);
      person.addEventListener("click", guarded("person", requestPerson));
      var error = el("span", "aw-person-error");
      error.setAttribute("role", "alert");
      row.appendChild(person);
      row.appendChild(error);
      return { row: row, person: person, label: label, error: error };
    }

    function buildFooter() {
      var row = el("p", "aw-footer");
      var note = el("span", "");
      row.appendChild(note);
      var privacy = null;
      if (typeof config.privacy_url === "string" && WEB_LINK_PATTERN.test(config.privacy_url)) {
        row.appendChild(document.createTextNode(" · "));
        privacy = el("a", "aw-privacy");
        privacy.href = config.privacy_url;
        privacy.target = "_blank";
        privacy.rel = "noopener noreferrer";
        row.appendChild(privacy);
      }
      return { row: row, note: note, privacy: privacy };
    }

    // The texts of the parts above in the interface language.
    function applyChromeLanguage() {
      restartButton.setAttribute("aria-label", text("newChat"));
      restartButton.title = text("newChat");
      if (contacts) {
        contacts.row.setAttribute("aria-label", text("otherWays"));
        contacts.items.forEach(function (item) {
          item.name.textContent = CONTACT_NAMES[item.kind] || text("call");
        });
      }
      confirm.question.textContent = text("newChatConfirm");
      confirm.yes.textContent = text("newChatYes");
      confirm.no.textContent = text("cancel");
      starters.row.setAttribute("aria-label", text("suggestions"));
      actions.label.textContent = text("person");
      footer.note.textContent = text("footer");
      if (footer.privacy) {
        footer.privacy.textContent = text("privacy");
      }
    }

    // Chips before the visitor's first message, in the interface language;
    // "Talk to a person" until staff have the conversation.
    function renderActions() {
      while (starters.row.firstChild) {
        starters.row.removeChild(starters.row.firstChild);
      }
      var hasWritten = state.history.some(function (item) {
        return item.role === "visitor";
      });
      var questions = hasWritten || state.isSending ? [] : starterQuestions(config, state.language);
      questions.forEach(function (question) {
        var chip = el("button", "aw-starter");
        chip.type = "button";
        chip.setAttribute("dir", "auto");
        chip.textContent = question;
        chip.addEventListener(
          "click",
          guarded("send", function () {
            input.value = question;
            submit();
          })
        );
        starters.row.appendChild(chip);
      });
      starters.row.hidden = questions.length === 0;
      actions.row.hidden = state.isHandedOff;
      actions.person.disabled = state.isRequestingPerson;
      actions.person.setAttribute("aria-busy", state.isRequestingPerson ? "true" : "false");
      actions.error.textContent = state.personError;
    }

    function requestPerson() {
      if (state.isRequestingPerson || state.isHandedOff || isLivePreview) {
        return;
      }
      state.isRequestingPerson = true;
      state.personError = "";
      renderActions();
      requestJson(
        handoffUrl,
        withVisitSource({ session_key: state.sessionKey, language: state.language })
      ).then(
        guarded("person", function (result) {
          state.isRequestingPerson = false;
          if (result.ok && result.body) {
            receiveHandoff(result.body);
          } else {
            refusePerson(result.status === 429 ? text("rateLimited") : personErrorText(result.status));
          }
        }),
        function () {
          state.isRequestingPerson = false;
          refusePerson(text("personFailed"));
        }
      );
    }

    function personErrorText(statusCode) {
      return statusCode === 404 || statusCode === 409 ? text("unavailable") : text("personFailed");
    }

    function refusePerson(message) {
      state.personError = message;
      announce(message);
      renderActions();
    }

    // Staff have the conversation: show what the visitor was told (in their
    // language, else the widget's own notice) once; polling skips it by id.
    function receiveHandoff(body) {
      var id = typeof body.message_id === "string" ? body.message_id : undefined;
      if (typeof body.text === "string" && body.text && isSameLanguage(body.language, state.language)) {
        state.history.push({
          role: "assistant",
          id: id,
          text: body.text,
          direction: body.direction === "rtl" ? "rtl" : "ltr"
        });
        announce(body.text);
      } else if (id || !state.handoffNoticeShown) {
        state.history.push({ role: "notice", key: "handedOff", id: id });
        announce(text("handedOff"));
      } else {
        announce(text("handedOff"));
      }
      state.handoffNoticeShown = true;
      if (!state.cursor && id) {
        saveCursor(id);
      }
      setHandedOff(true);
      markActivity();
      saveHistory();
      renderLog();
      state.pollDelay = POLL_FIRST_DELAY_MS;
      schedulePoll(POLL_FIRST_DELAY_MS);
    }

    function askRestart() {
      if (!state.history.length && !state.isHandedOff) {
        input.focus();
        return;
      }
      setConfirmingRestart(true);
      confirm.yes.focus();
    }

    function setConfirmingRestart(isConfirming) {
      state.isConfirmingRestart = isConfirming;
      confirm.row.hidden = !isConfirming;
    }

    // A new visitor key: the next message starts a new conversation (staff
    // keep the old one in the cabinet). Other tabs follow the stored key.
    function restartConversation() {
      if (state.isSending) {
        return;
      }
      stopPolling();
      state.sessionKey = replaceSessionKey();
      forgetConversation();
      setConfirmingRestart(false);
      saveHistory();
      renderLog();
      announce(text("newChat"));
      input.focus();
    }

    function adoptStoredSession() {
      var stored = storageGet(localStorageOrNull(), storagePrefix + "session");
      if (stored && stored !== state.sessionKey && SESSION_KEY_PATTERN.test(stored)) {
        stopPolling();
        state.sessionKey = stored;
        forgetConversation();
        state.storedHistory = storageGet(localStorageOrNull(), storagePrefix + "history");
        renderLog();
      }
    }

    function forgetConversation() {
      state.history = [];
      state.pendingItem = null;
      state.handoffNoticeShown = false;
      state.isHandedOff = false;
      state.handoffAt = 0;
      state.activityAt = 0;
      state.cursor = null;
      state.personError = "";
      state.pollStopped = false;
      clearConversationState();
    }
