    // --- thumbs up or down under an answer --------------------------------

    // The answers this browser rated (so the thumbs do not come back).
    function loadRated() {
      try {
        var parsed = JSON.parse(storageGet(localStorageOrNull(), storagePrefix + "rated") || "[]");
        return Array.isArray(parsed)
          ? parsed
              .filter(function (id) {
                return typeof id === "string";
              })
              .slice(-MAX_RATED_ANSWERS)
          : [];
      } catch (error) {
        return [];
      }
    }

    function rememberRated(answerId, isRated) {
      state.rated = state.rated.filter(function (id) {
        return id !== answerId;
      });
      if (isRated) {
        state.rated.push(answerId);
      }
      state.rated = state.rated.slice(-MAX_RATED_ANSWERS);
      storageSet(localStorageOrNull(), storagePrefix + "rated", JSON.stringify(state.rated));
    }

    // The last message when it is a stored answer of the assistant: the
    // thumbs go under it (not under a draft, a staff reply or a greeting).
    function lastAnswer() {
      var last = null;
      state.history.forEach(function (item) {
        if (item.role !== "notice") {
          last = item;
        }
      });
      if (!last || last.role !== "assistant" || !last.id || last.draft || isLivePreview) {
        return null;
      }
      return last;
    }

    // The thumbs show at once under an answer that booked or took a lead,
    // else once two minutes passed without a new message; then "what went
    // wrong?" after a thumbs down, then thanks.
    function appendRating() {
      window.clearTimeout(state.ratingTimer);
      state.ratingTimer = null;
      var answer = lastAnswer();
      if (!answer) {
        return;
      }
      if (state.ratingStep && state.ratingStep.id === answer.id) {
        log.appendChild(state.ratingStep.isAskingWhy ? reasonsRow(answer) : thanksRow());
        return;
      }
      if (state.rated.indexOf(answer.id) !== -1) {
        return;
      }
      var waited = Date.now() - state.activityAt;
      if (!answer.invitesRating && waited < RATING_IDLE_MS) {
        state.ratingTimer = window.setTimeout(guarded("render", renderLog), RATING_IDLE_MS - waited + 50);
        return;
      }
      log.appendChild(thumbsRow(answer));
    }

    function ratingRow(questionKey) {
      var row = el("div", "aw-rating");
      row.setAttribute("role", "group");
      row.setAttribute("aria-label", text(questionKey));
      var question = el("p", "aw-rating-text");
      question.textContent = text(questionKey);
      row.appendChild(question);
      return row;
    }

    function thumbsRow(answer) {
      var row = ratingRow("rateAsk");
      [
        ["good", "rateGood"],
        ["bad", "rateBad"]
      ].forEach(function (choice) {
        var button = el("button", "aw-rate aw-rate-" + choice[0]);
        button.type = "button";
        button.setAttribute("aria-label", text(choice[1]));
        button.title = text(choice[1]);
        button.appendChild(thumbIcon());
        button.addEventListener(
          "click",
          guarded("send", function () {
            rate(answer, choice[0], "");
          })
        );
        row.appendChild(button);
      });
      return row;
    }

    function reasonsRow(answer) {
      var row = ratingRow("rateWhy");
      RATING_REASONS.forEach(function (reason, index) {
        var chip = el("button", "aw-starter");
        chip.type = "button";
        chip.textContent = text(RATING_REASON_TEXTS[index]);
        chip.addEventListener(
          "click",
          guarded("send", function () {
            rate(answer, "bad", reason);
          })
        );
        row.appendChild(chip);
      });
      return row;
    }

    function thanksRow() {
      var row = el("p", "aw-rating");
      row.textContent = text("rateThanks");
      return row;
    }

    // Recorded at once in this browser; a rating the API did not take (too
    // many, the network) brings the thumbs back. A thumbs down is sent
    // right away and again with its reason when the visitor picks one.
    function rate(answer, rating, reason) {
      if (isLivePreview) {
        return;
      }
      rememberRated(answer.id, true);
      state.ratingStep = { id: answer.id, isAskingWhy: rating === "bad" && !reason };
      renderLog();
      if (state.ratingStep.isAskingWhy) {
        var firstReason = log.querySelector(".aw-rating .aw-starter");
        if (firstReason) {
          firstReason.focus();
        }
      } else {
        log.focus();
        announce(text("rateThanks"));
      }
      var body = { session_key: state.sessionKey, rating: rating, message_id: answer.id };
      if (reason) {
        body.reason = reason;
      }
      var takeBack = function () {
        if (!reason) {
          rememberRated(answer.id, false);
          state.ratingStep = null;
          renderLog();
        }
      };
      requestJson(ratingUrl, body).then(
        guarded("send", function (result) {
          if (!result.ok && result.status !== 404) {
            takeBack();
          }
        }),
        guarded("send", takeBack)
      );
    }
