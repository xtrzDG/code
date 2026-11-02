  // --- visitor identity and history (web storage, never cookies) ----------

  function loadSessionKey() {
    forgetIdleConversation();
    var storage = conversationStorageOrNull();
    var key = storageGet(storage, storagePrefix + "session");
    if (key && SESSION_KEY_PATTERN.test(key)) {
      return key;
    }
    key = "v1_" + randomString(32);
    storageSet(storage, storagePrefix + "session", key);
    return key;
  }

  // A new visitor key (a new conversation): the others are forgotten.
  function replaceSessionKey() {
    var key = "v1_" + randomString(32);
    storageSet(conversationStorageOrNull(), storagePrefix + "session", key);
    return key;
  }

  // A conversation idle for CONVERSATION_IDLE_EXPIRY_MS is over: its
  // transcript, position and visitor key leave the device (the API would
  // hand the old messages back to the old key). A history saved before
  // its time was stamped starts the idle clock now. On the chat page a
  // conversation an earlier version kept on the device is removed.
  function forgetIdleConversation() {
    if (isPageMode) {
      forgetConversationOn(localStorageOrNull());
    }
    var storage = conversationStorageOrNull();
    var lastAt = Math.max(
      Number(storageGet(storage, storagePrefix + "activity-at")) || 0,
      Number(storageGet(storage, storagePrefix + "history-at")) || 0
    );
    if (lastAt === 0) {
      if (storageGet(storage, storagePrefix + "history")) {
        storageSet(storage, storagePrefix + "history-at", String(Date.now()));
      }
      return;
    }
    if (Date.now() - lastAt <= CONVERSATION_IDLE_EXPIRY_MS) {
      return;
    }
    forgetConversationOn(storage);
  }

  function forgetConversationOn(storage) {
    CONVERSATION_STORAGE_KEYS.forEach(function (name) {
      storageRemove(storage, storagePrefix + name);
    });
  }

  function clearConversationState() {
    var storage = conversationStorageOrNull();
    storageSet(storage, storagePrefix + "cursor", "");
    storageSet(storage, storagePrefix + "handoff", "0");
    storageSet(storage, storagePrefix + "handoff-at", "0");
    storageSet(storage, storagePrefix + "activity-at", "0");
  }

  function loadHistory() {
    var raw = storageGet(conversationStorageOrNull(), storagePrefix + "history");
    if (!raw) {
      return [];
    }
    try {
      var parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return [];
      }
      return parsed
        .filter(function (item) {
          return (
            item &&
            (item.role === "notice" ||
              ((item.role === "visitor" || item.role === "assistant" || item.role === "staff") &&
                typeof item.text === "string"))
          );
        })
        .slice(-MAX_STORED_MESSAGES)
        .map(function (item) {
          return {
            role: item.role,
            id: typeof item.id === "string" ? item.id : undefined,
            text: item.text,
            direction: item.direction === "rtl" ? "rtl" : "ltr",
            key: item.key,
            // A stream's text the next poll replaces with the stored one.
            draft: item.draft === true,
            pending: item.pending === true,
            sentAt: typeof item.sentAt === "number" ? item.sentAt : 0,
            failed: false,
            choices: readChoices(item.choices),
            attachments: readAttachments(item.attachments),
            invitesRating: item.invitesRating === true
          };
        });
    } catch (error) {
      return [];
    }
  }

  // The options an assistant reply offers (chips under it until the
  // visitor writes): short non-empty texts, at most MAX_CHOICES.
  function readChoices(value) {
    if (!Array.isArray(value)) {
      return [];
    }
    return value
      .filter(function (choice) {
        return typeof choice === "string" && choice.trim() !== "" && choice.length <= MAX_CHOICE_LENGTH;
      })
      .slice(0, MAX_CHOICES);
  }

  // The photos and voice messages a visitor message carried: their ids,
  // kinds and lengths (the files stay on the API, the pictures on the page
  // that sent them).
  function readAttachments(value) {
    if (!Array.isArray(value)) {
      return [];
    }
    return value
      .filter(function (attachment) {
        return (
          attachment &&
          typeof attachment.id === "string" &&
          ATTACHMENT_ID_PATTERN.test(attachment.id) &&
          (attachment.kind === "image" || attachment.kind === "audio")
        );
      })
      .slice(0, MAX_ATTACHMENTS)
      .map(function (attachment) {
        return {
          id: attachment.id,
          kind: attachment.kind,
          seconds: Math.max(0, Math.round(Number(attachment.seconds) || 0))
        };
      });
  }

  // The script's data-source, else ?src= or ?utm_source= of the page,
  // kept for the tab, so a visitor who came by a QR code and opened
  // another page before writing still counts for that code.
  function loadVisitSource() {
    var storage = sessionStorageOrNull();
    var found = (
      script.getAttribute("data-source") ||
      readPageParameter("src") ||
      readPageParameter("utm_source") ||
      ""
    )
      .trim()
      .slice(0, MAX_SOURCE_LENGTH);
    if (found) {
      storageSet(storage, storagePrefix + "source", found);
      return found;
    }
    return storageGet(storage, storagePrefix + "source") || "";
  }

  function readPageParameter(name) {
    try {
      return new URLSearchParams(window.location.search).get(name) || "";
    } catch (error) {
      return "";
    }
  }

  // A message or handoff body with the visitor's source, when known.
  function withVisitSource(body) {
    if (visitSource) {
      body.source = visitSource;
    }
    return body;
  }

  function randomString(length) {
    var values = new Uint8Array(length);
    var cryptoSource = window.crypto || window.msCrypto;
    if (cryptoSource && cryptoSource.getRandomValues) {
      cryptoSource.getRandomValues(values);
    } else {
      for (var fill = 0; fill < length; fill += 1) {
        values[fill] = Math.floor(Math.random() * 256);
      }
    }
    var result = "";
    for (var index = 0; index < length; index += 1) {
      result += SESSION_KEY_ALPHABET.charAt(values[index] % SESSION_KEY_ALPHABET.length);
    }
    return result;
  }

  // The live preview keeps everything in memory: the owner's browser shares
  // the origin with the hosted chat page, whose visitors' keys stay apart.
  function localStorageOrNull() {
    if (isLivePreview) {
      return null;
    }
    try {
      return window.localStorage;
    } catch (error) {
      return null;
    }
  }

  // Where a conversation is kept (its visitor key, transcript, position,
  // handoff and last activity): the chat page (data-mode="page", the
  // hosted chat) keeps it for the tab only, so the transcript leaves with
  // the tab; a site's widget keeps it on the device until it goes idle.
  function conversationStorageOrNull() {
    return isPageMode ? sessionStorageOrNull() : localStorageOrNull();
  }

  function sessionStorageOrNull() {
    if (isLivePreview) {
      return null;
    }
    try {
      return window.sessionStorage;
    } catch (error) {
      return null;
    }
  }

  function storageGet(storage, key) {
    try {
      if (storage) {
        return storage.getItem(key);
      }
    } catch (error) {
      // Storage blocked (privacy mode): keep the value in memory.
    }
    return Object.prototype.hasOwnProperty.call(memoryStorage, key) ? memoryStorage[key] : null;
  }

  function storageRemove(storage, key) {
    delete memoryStorage[key];
    try {
      if (storage) {
        storage.removeItem(key);
      }
    } catch (error) {
      // Storage blocked: nothing was kept there.
    }
  }

  function storageSet(storage, key, value) {
    memoryStorage[key] = value;
    try {
      if (storage) {
        storage.setItem(key, value);
      }
    } catch (error) {
      // Quota or privacy mode: the in-memory copy is enough for this page.
    }
  }

