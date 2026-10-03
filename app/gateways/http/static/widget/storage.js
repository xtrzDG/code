  // --- visitor identity and history (localStorage, never cookies) ---------

  function loadSessionKey() {
    var storage = localStorageOrNull();
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
    storageSet(localStorageOrNull(), storagePrefix + "session", key);
    return key;
  }

  function clearConversationState() {
    var storage = localStorageOrNull();
    storageSet(storage, storagePrefix + "cursor", "");
    storageSet(storage, storagePrefix + "handoff", "0");
    storageSet(storage, storagePrefix + "handoff-at", "0");
    storageSet(storage, storagePrefix + "activity-at", "0");
  }

  function loadHistory() {
    var raw = storageGet(localStorageOrNull(), storagePrefix + "history");
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
            pending: item.pending === true,
            sentAt: typeof item.sentAt === "number" ? item.sentAt : 0,
            failed: false
          };
        });
    } catch (error) {
      return [];
    }
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

  function localStorageOrNull() {
    try {
      return window.localStorage;
    } catch (error) {
      return null;
    }
  }

  function sessionStorageOrNull() {
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

