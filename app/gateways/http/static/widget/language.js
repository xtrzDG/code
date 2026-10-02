  // --- language ----------------------------------------------------------

  function chooseLanguage(config) {
    var languages = Array.isArray(config.languages) ? config.languages : [];
    var tags = languages.map(function (language) {
      return String(language.tag);
    });
    var candidates = [];
    var forced = script.getAttribute("data-language");
    if (forced) {
      candidates.push(forced);
    }
    var saved = storageGet(localStorageOrNull(), storagePrefix + "language");
    if (saved) {
      candidates.push(saved);
    }
    var browserLanguages = navigator.languages && navigator.languages.length
      ? navigator.languages
      : [navigator.language || ""];
    candidates = candidates.concat(Array.prototype.slice.call(browserLanguages));
    for (var index = 0; index < candidates.length; index += 1) {
      var match = matchLanguage(String(candidates[index] || ""), tags);
      if (match) {
        return match;
      }
    }
    if (config.default_language && tags.indexOf(config.default_language) !== -1) {
      return config.default_language;
    }
    return tags.length ? tags[0] : config.default_language || "en";
  }

  function matchLanguage(candidate, tags) {
    if (!candidate) {
      return null;
    }
    var lower = candidate.toLowerCase();
    var index;
    for (index = 0; index < tags.length; index += 1) {
      if (tags[index].toLowerCase() === lower) {
        return tags[index];
      }
    }
    var base = baseLanguage(lower);
    for (index = 0; index < tags.length; index += 1) {
      if (baseLanguage(tags[index].toLowerCase()) === base) {
        return tags[index];
      }
    }
    return null;
  }

  function baseLanguage(tag) {
    return String(tag).split(/[-_]/)[0].toLowerCase();
  }

  function languageDirection(config, tag) {
    var languages = Array.isArray(config.languages) ? config.languages : [];
    for (var index = 0; index < languages.length; index += 1) {
      if (languages[index].tag === tag) {
        return languages[index].direction === "rtl" ? "rtl" : "ltr";
      }
    }
    return RTL_LANGUAGES.indexOf(baseLanguage(tag)) !== -1 ? "rtl" : "ltr";
  }

  // The business's greeting for the language (exact tag, then base language).
  // A language in its own name as a picker label: "русский" -> "Русский".
  // Georgian (Mkhedruli) has no capitals: uppercasing gives Mtavruli.
  function pickerLabel(language) {
    var name = String(language.native_name || language.tag || "");
    if (!name || /^[\u10D0-\u10FF]/.test(name)) {
      return name;
    }
    var first = name.charAt(0);
    try {
      first = first.toLocaleUpperCase(language.tag);
    } catch (error) {
      first = first.toUpperCase();
    }
    return first + name.slice(1);
  }

  function configGreeting(config, tag) {
    var greetings = Array.isArray(config.greetings) ? config.greetings : [];
    var base = null;
    for (var index = 0; index < greetings.length; index += 1) {
      var greeting = greetings[index];
      if (!greeting || typeof greeting.text !== "string" || !greeting.text) {
        continue;
      }
      if (String(greeting.language).toLowerCase() === String(tag).toLowerCase()) {
        return { text: greeting.text, direction: greeting.direction };
      }
      if (!base && baseLanguage(greeting.language) === baseLanguage(tag)) {
        base = { text: greeting.text, direction: greeting.direction };
      }
    }
    return base;
  }

  // The script tag's data-color wins over the colour chosen in the cabinet.
  function chooseAccent(attribute, configured) {
    var candidates = [String(attribute || "").trim(), String(configured || "").trim()];
    for (var index = 0; index < candidates.length; index += 1) {
      if (COLOR_PATTERN.test(candidates[index])) {
        return candidates[index];
      }
    }
    return "";
  }

  function choosePosition(attribute, configured) {
    var fromTag = String(attribute || "").trim().toLowerCase();
    if (POSITIONS.indexOf(fromTag) !== -1) {
      return fromTag;
    }
    var fromConfig = String(configured || "").trim().toLowerCase();
    return POSITIONS.indexOf(fromConfig) !== -1 ? fromConfig : "right";
  }

  function translate(tag, key) {
    var exact = TEXTS[String(tag).toLowerCase()];
    var base = TEXTS[baseLanguage(tag)];
    if (exact && exact[key]) {
      return exact[key];
    }
    if (base && base[key]) {
      return base[key];
    }
    return TEXTS.en[key] || key;
  }

