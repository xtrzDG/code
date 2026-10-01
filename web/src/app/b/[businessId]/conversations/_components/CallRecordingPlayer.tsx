"use client";

import { useRef, useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { callRecordingUrl } from "./conversationModel";

/**
 * The browser's own audio player for one call recording. `preload="none"`:
 * nothing is fetched (and nothing written to the audit log) until someone
 * presses play; the audio then streams from the voice platform through the
 * API. A recording that cannot be loaded (deleted after the retention
 * period, the platform unreachable, the session expired) shows why and can
 * be tried again.
 */
export function CallRecordingPlayer({ callId, label }: { callId: string; label: string }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const audio = useRef<HTMLAudioElement>(null);
  const [failed, setFailed] = useState(false);

  const retry = () => {
    const player = audio.current;
    if (!player) {
      return;
    }
    setFailed(false);
    player.load();
    void player.play().catch(() => {
      // The error event reports the failure; a refused autoplay needs nothing.
    });
  };

  return (
    <div className="space-y-2">
      <audio
        ref={audio}
        controls
        preload="none"
        src={callRecordingUrl(business.id, callId)}
        aria-label={label}
        onError={() => setFailed(true)}
        onPlaying={() => setFailed(false)}
        className="block h-10 w-full max-w-md"
      >
        {t("conversations.calls.playerUnsupported")}
      </audio>
      {failed ? (
        <Alert
          tone="danger"
          action={
            <Button variant="secondary" size="sm" onClick={retry}>
              {t("conversations.calls.playRetry")}
            </Button>
          }
        >
          {t("conversations.calls.playError")}
        </Alert>
      ) : null}
    </div>
  );
}
