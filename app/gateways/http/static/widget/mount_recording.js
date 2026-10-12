    // --- voice messages: hold the microphone ------------------------------

    // The recording format of this browser the API takes; "" hides the
    // microphone (no MediaRecorder, no microphone access, no common format).
    function recordingType() {
      if (
        typeof window.MediaRecorder !== "function" ||
        !navigator.mediaDevices ||
        typeof navigator.mediaDevices.getUserMedia !== "function"
      ) {
        return "";
      }
      var accepted = audioTypes();
      for (var index = 0; index < RECORDING_TYPES.length; index += 1) {
        var type = RECORDING_TYPES[index];
        var isSupported = false;
        try {
          isSupported = window.MediaRecorder.isTypeSupported(type);
        } catch (error) {
          isSupported = false;
        }
        if (isSupported && accepted.indexOf(type.split(";")[0]) !== -1) {
          return type;
        }
      }
      return "";
    }

    // Pressed: record. Released: send. The pointer left the button, the
    // press was cancelled or Escape: discard. Space and Enter work the same.
    function bindRecorder(mic) {
      mic.addEventListener(
        "pointerdown",
        guarded("send", function (event) {
          if (event.button === 0 || event.button === undefined) {
            event.preventDefault();
            startRecording();
          }
        })
      );
      mic.addEventListener("pointerup", function () {
        stopRecording(true);
      });
      ["pointerleave", "pointercancel", "blur"].forEach(function (name) {
        mic.addEventListener(name, function () {
          stopRecording(false);
        });
      });
      mic.addEventListener("contextmenu", function (event) {
        event.preventDefault();
      });
      mic.addEventListener(
        "keydown",
        guarded("send", function (event) {
          if ((event.key === " " || event.key === "Enter") && !event.repeat) {
            event.preventDefault();
            startRecording();
          } else if (event.key === "Escape" && state.recording) {
            event.stopPropagation();
            stopRecording(false);
          }
        })
      );
      mic.addEventListener("keyup", function (event) {
        if (event.key === " " || event.key === "Enter") {
          event.preventDefault();
          stopRecording(true);
        }
      });
    }

    function startRecording() {
      var type = recordingType();
      if (state.recording || !type || isLivePreview || state.isSending) {
        return;
      }
      if (currentUploads().length >= MAX_ATTACHMENTS) {
        showMediaError(text("tooMany"));
        return;
      }
      var recording = {
        type: type,
        startedAt: Date.now(),
        chunks: [],
        stream: null,
        recorder: null,
        isStopping: false,
        keep: false,
        ticker: null,
        limit: null
      };
      state.recording = recording;
      state.mediaError = "";
      renderTray();
      navigator.mediaDevices.getUserMedia({ audio: true }).then(
        guarded("send", function (stream) {
          recording.stream = stream;
          if (state.recording !== recording) {
            // Released while the browser asked for the microphone.
            stopTracks(recording);
            announce(text("record"));
            return;
          }
          beginRecorder(recording);
        }),
        guarded("send", function () {
          if (state.recording === recording) {
            state.recording = null;
          }
          showMediaError(text("micBlocked"));
        })
      );
    }

    function beginRecorder(recording) {
      var recorder = new window.MediaRecorder(recording.stream, { mimeType: recording.type });
      recording.recorder = recorder;
      recording.startedAt = Date.now();
      recorder.addEventListener("dataavailable", function (event) {
        if (event.data && event.data.size) {
          recording.chunks.push(event.data);
        }
      });
      recorder.addEventListener(
        "stop",
        guarded("send", function () {
          finishRecording(recording);
        })
      );
      recorder.start();
      recording.ticker = window.setInterval(guarded("render", renderTray), 1000);
      var limitSeconds = ruleNumber("max_voice_seconds");
      if (limitSeconds) {
        // Stopped just under the API's limit.
        recording.limit = window.setTimeout(function () {
          stopRecording(true);
        }, limitSeconds * 1000 - 250);
      }
      announce(text("recording"));
      renderTray();
    }

    function stopRecording(keep) {
      var recording = state.recording;
      if (!recording || recording.isStopping) {
        return;
      }
      recording.isStopping = true;
      recording.keep = keep;
      window.clearInterval(recording.ticker);
      window.clearTimeout(recording.limit);
      if (recording.recorder && recording.recorder.state !== "inactive") {
        // The recorder's "stop" event finishes it.
        recording.recorder.stop();
        return;
      }
      state.recording = null;
      renderTray();
    }

    // Kept when held long enough: uploaded like a photo, with its length.
    function finishRecording(recording) {
      stopTracks(recording);
      if (state.recording === recording) {
        state.recording = null;
      }
      var elapsed = Date.now() - recording.startedAt;
      renderTray();
      if (!recording.keep) {
        return;
      }
      if (elapsed < MIN_RECORDING_MS) {
        announce(text("record"));
        return;
      }
      var type = recording.recorder.mimeType || recording.type;
      var file = new Blob(recording.chunks, { type: type });
      var limitBytes = ruleNumber("max_voice_bytes");
      if (limitBytes && file.size > limitBytes) {
        showMediaError(text("fileTooLarge"));
        return;
      }
      upload(file, "audio", "voice" + fileExtension(type), Math.max(1, Math.round(elapsed / 1000)));
    }

    function stopTracks(recording) {
      if (recording.stream && typeof recording.stream.getTracks === "function") {
        recording.stream.getTracks().forEach(function (track) {
          track.stop();
        });
      }
    }
