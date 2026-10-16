"use client";

import { useEffect, useRef, useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlay } from "@/components/icons";
import { Alert, Button, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { loginPath } from "@/lib/navigation";

import { messageMediaUrl } from "../../_lib/messageMedia";
import { loadRecording } from "../../_lib/recordingLoader";

type PlayerProblem = "missing" | "failed" | null;

/**
 * A customer's voice message. Like a call recording, nothing is fetched
 * (and nothing written to the audit log) until someone presses play; the
 * file is then downloaded once and played from memory, so every browser can
 * seek in it. An expired session goes to the sign-in page, a deleted file
 * says so, an outage can be tried again; focus stays on what replaces the
 * pressed button.
 */
export function VoiceNotePlayer({ mediaId }: { mediaId: string }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const audio = useRef<HTMLAudioElement>(null);
  const isMounted = useRef(false);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [problem, setProblem] = useState<PlayerProblem>(null);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (!objectUrl) {
      return undefined;
    }
    const player = audio.current;
    if (player) {
      player.focus();
      void player.play().catch(() => {
        // Playing right after a download may be refused (iOS): the
        // player's own button works.
      });
    }
    return () => URL.revokeObjectURL(objectUrl);
  }, [objectUrl]);

  const load = async () => {
    if (isLoading) {
      return;
    }
    setIsLoading(true);
    const result = await loadRecording(messageMediaUrl(business.id, mediaId));
    if (!isMounted.current) {
      return;
    }
    setIsLoading(false);
    if (result.ok) {
      setProblem(null);
      setObjectUrl(URL.createObjectURL(result.blob));
      return;
    }
    if (result.failure === "expired") {
      const next = `${window.location.pathname}${window.location.search}`;
      window.location.assign(loginPath({ next, reason: "expired" }));
      return;
    }
    setProblem(result.failure === "missing" ? "missing" : "failed");
  };

  const busyIcon = isLoading ? <Spinner size="sm" /> : undefined;

  if (objectUrl) {
    return (
      <audio
        ref={audio}
        controls
        src={objectUrl}
        aria-label={t("conversationMedia.voice.playerLabel")}
        onError={() => setProblem("failed")}
        className="block h-10 w-full min-w-0 max-w-xs"
      >
        {t("conversationMedia.voice.playerUnsupported")}
      </audio>
    );
  }

  return (
    <div className="space-y-2">
      {problem === null ? (
        <Button
          variant="secondary"
          size="sm"
          aria-label={t("conversationMedia.voice.playLabel")}
          aria-busy={isLoading || undefined}
          aria-disabled={isLoading || undefined}
          leadingIcon={busyIcon ?? <IconPlay className="size-4" aria-hidden />}
          onClick={() => void load()}
        >
          {isLoading ? t("conversationMedia.voice.loading") : t("conversationMedia.voice.play")}
        </Button>
      ) : null}
      {problem === "missing" ? <Alert tone="warning">{t("conversationMedia.voice.missing")}</Alert> : null}
      {problem === "failed" ? (
        <Alert
          tone="danger"
          action={
            <Button
              variant="secondary"
              size="sm"
              aria-busy={isLoading || undefined}
              aria-disabled={isLoading || undefined}
              leadingIcon={busyIcon}
              onClick={() => void load()}
            >
              {t("conversationMedia.voice.retry")}
            </Button>
          }
        >
          {t("conversationMedia.voice.error")}
        </Alert>
      ) : null}
    </div>
  );
}
