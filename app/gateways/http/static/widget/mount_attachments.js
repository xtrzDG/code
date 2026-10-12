    // --- photos and voice messages: the paperclip and the tray -----------

    // The paperclip (with its hidden file picker), the microphone and the
    // tray of what the next message carries. Each is hidden when the API's
    // config names no type of its kind.
    function buildMedia() {
      var tray = el("div", "aw-tray");
      tray.hidden = true;
      var attach = el("button", "aw-tool aw-attach");
      attach.type = "button";
      attach.appendChild(attachIcon());
      attach.hidden = imageTypes().length === 0;
      var picker = el("input", "aw-sr");
      picker.type = "file";
      picker.accept = imageTypes().join(",");
      picker.multiple = true;
      picker.tabIndex = -1;
      picker.setAttribute("aria-hidden", "true");
      attach.addEventListener("click", function () {
        if (!isLivePreview) {
          picker.click();
        }
      });
      picker.addEventListener(
        "change",
        guarded("send", function () {
          var files = Array.prototype.slice.call(picker.files || []);
          picker.value = "";
          files.forEach(addPhoto);
        })
      );
      var mic = el("button", "aw-tool aw-mic");
      mic.type = "button";
      mic.appendChild(micIcon());
      mic.hidden = recordingType() === "";
      bindRecorder(mic);
      return { tray: tray, attach: attach, picker: picker, mic: mic };
    }

    // What the API takes (GET .../config `attachments`); it checks it all again.
    function typeList(name) {
      var rules = config.attachments;
      var list = rules && Array.isArray(rules[name]) ? rules[name] : [];
      return list.filter(function (type) {
        return typeof type === "string" && /^[a-z]+\/[a-z0-9.+-]+$/.test(type);
      });
    }

    function imageTypes() {
      return typeList("image_types");
    }

    function audioTypes() {
      return typeList("audio_types");
    }

    function ruleNumber(name) {
      var value = config.attachments ? Number(config.attachments[name]) : 0;
      return value > 0 ? value : 0;
    }

    // Uploads of the current visitor key: those of a conversation left
    // behind ("New conversation") are not the new visitor's to send.
    function currentUploads() {
      return state.uploads.filter(function (upload) {
        return upload.sessionKey === state.sessionKey;
      });
    }

    function readyUploads() {
      return currentUploads().filter(function (upload) {
        return Boolean(upload.id);
      });
    }

    function isUploading() {
      return currentUploads().length > readyUploads().length;
    }

    function addPhoto(file) {
      if (currentUploads().length >= MAX_ATTACHMENTS) {
        showMediaError(text("tooMany"));
      } else if (imageTypes().indexOf(String(file.type).toLowerCase()) === -1) {
        showMediaError(text("fileType"));
      } else if (ruleNumber("max_image_bytes") && file.size > ruleNumber("max_image_bytes")) {
        showMediaError(text("fileTooLarge"));
      } else {
        upload(file, "image", "photo" + fileExtension(file.type), 0);
      }
    }

    // Uploaded at once (the API checks the file's bytes, strips a photo's
    // metadata and measures a recording); the message only names it.
    function upload(file, kind, fileName, seconds) {
      var entry = {
        kind: kind,
        sessionKey: state.sessionKey,
        id: "",
        seconds: seconds,
        url: kind === "image" ? objectUrl(file) : ""
      };
      state.uploads.push(entry);
      state.mediaError = "";
      renderTray();
      updateSendButton();
      requestUpload(attachmentsUrl, file, fileName, state.sessionKey).then(
        guarded("send", function (result) {
          var id = result.body && result.body.attachment_id;
          if (result.status === 201 && typeof id === "string" && ATTACHMENT_ID_PATTERN.test(id)) {
            entry.id = id;
            if (entry.url) {
              state.mediaUrls[id] = entry.url;
            }
          } else {
            dropUpload(entry, uploadErrorText(result));
          }
          renderTray();
          updateSendButton();
        }),
        guarded("send", function () {
          dropUpload(entry, text("fileFailed"));
          renderTray();
          updateSendButton();
        })
      );
    }

    // The API's reason (422 with its code), its limits and outages in the
    // visitor's words.
    function uploadErrorText(result) {
      var reasons = result.body && Array.isArray(result.body.reasons) ? result.body.reasons : [];
      var code = reasons.length && reasons[0] ? String(reasons[0].code) : "";
      if (code === "file_too_large" || result.status === 413) {
        return text("fileTooLarge");
      }
      if (code === "voice_too_long") {
        return text("voiceTooLong");
      }
      if (code === "unsupported_type" || code === "type_mismatch") {
        return text("fileType");
      }
      if (result.status === 429) {
        return text("rateLimited");
      }
      return result.status === 404 || result.status === 409 ? text("unavailable") : text("fileFailed");
    }

    function dropUpload(entry, message) {
      removeEntry(entry);
      if (message) {
        showMediaError(message);
      }
    }

    function removeEntry(entry) {
      state.uploads = state.uploads.filter(function (upload) {
        return upload !== entry;
      });
      if (entry.url && !entry.id) {
        revokeUrl(entry.url);
      }
    }

    function showMediaError(message) {
      state.mediaError = message;
      renderTray();
      announce(message);
    }

    // The uploads the message sends, out of the tray (their pictures stay
    // for the conversation's thumbnails on this page).
    function takeAttachments() {
      var taken = readyUploads();
      state.uploads = state.uploads.filter(function (upload) {
        return taken.indexOf(upload) === -1;
      });
      state.mediaError = "";
      renderTray();
      return taken.map(function (upload) {
        return { id: upload.id, kind: upload.kind, seconds: upload.seconds };
      });
    }

    function messageBody(item) {
      var body = { session_key: state.sessionKey };
      if (item.text) {
        body.text = item.text;
      }
      var ids = (item.attachments || []).map(function (attachment) {
        return attachment.id;
      });
      if (ids.length) {
        body.attachment_ids = ids;
      }
      return withVisitSource(body);
    }

    function renderTray() {
      var tray = media.tray;
      while (tray.firstChild) {
        tray.removeChild(tray.firstChild);
      }
      var uploads = currentUploads();
      uploads.forEach(function (entry) {
        tray.appendChild(trayItem(entry));
      });
      if (state.recording) {
        var recorder = el("p", "aw-recorder");
        recorder.textContent = text("recording") + " " + clock((Date.now() - state.recording.startedAt) / 1000);
        tray.appendChild(recorder);
      }
      var error = el("p", "aw-media-error");
      error.textContent = state.mediaError;
      tray.appendChild(error);
      tray.hidden = !uploads.length && !state.recording && !state.mediaError;
      media.attach.disabled = uploads.length >= MAX_ATTACHMENTS || isLivePreview;
      media.mic.disabled = (uploads.length >= MAX_ATTACHMENTS && !state.recording) || isLivePreview;
      media.mic.classList.toggle("aw-recording", Boolean(state.recording));
      media.mic.setAttribute("aria-pressed", state.recording ? "true" : "false");
    }

    function trayItem(entry) {
      var item = el("div", "aw-tray-item");
      item.setAttribute("aria-busy", entry.id ? "false" : "true");
      if (!entry.id) {
        item.title = text("uploading");
      }
      if (entry.url) {
        var image = el("img", "");
        image.src = entry.url;
        image.alt = text("photo");
        item.appendChild(image);
      } else {
        item.appendChild(fileLabel(entry));
      }
      var remove = el("button", "aw-remove");
      remove.type = "button";
      remove.setAttribute("aria-label", text("remove"));
      remove.title = text("remove");
      remove.appendChild(closeIcon());
      remove.addEventListener("click", function () {
        removeEntry(entry);
        state.mediaError = "";
        renderTray();
        updateSendButton();
        input.focus();
      });
      item.appendChild(remove);
      return item;
    }

    function fileExtension(type) {
      var base = String(type).split(";")[0].toLowerCase();
      var known = { "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp" };
      known["audio/webm"] = ".webm";
      known["audio/ogg"] = ".ogg";
      known["audio/mp4"] = ".m4a";
      return known[base] || "";
    }

    function objectUrl(file) {
      try {
        return window.URL && window.URL.createObjectURL ? window.URL.createObjectURL(file) : "";
      } catch (error) {
        return "";
      }
    }

    function revokeUrl(url) {
      try {
        window.URL.revokeObjectURL(url);
      } catch (error) {
        // Nothing to free.
      }
    }
