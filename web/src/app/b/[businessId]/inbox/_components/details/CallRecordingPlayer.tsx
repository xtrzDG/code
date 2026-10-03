"use client";

import { useEffect, useRef, useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconPlay } from "@/components/icons";
import { Alert, Button, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { loginPath } from "@/lib/navigation";

import { callRecordingUrl } from "../../_lib/conversationModel";
import { loadRecording } from "../../_lib/recordingLoader";

type PlayerProblem = "missing" | "failed" | null;

/**
 * One call recording. Nothing is fetched (and nothing written to the audit
 * log) until someone presses play; the recording is then downloaded once
 * and played from memory, so the browser's player can seek anywhere and
 * Safari and iOS play it too. An expired session goes to the sign-in page;
 * a deleted recording says so; a service that does not answer can be
 * tried again. Keyboard focus stays on what replaces the pressed button.
 */
export function CallRecordingPlayer({ callId, label, playLabel }: { callId: string; label: string; playLabel: string }) {
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
      // The pressed button is gone: keyboard and screen-reader focus moves
      // to the player instead of falling back to the page.
      player.focus();
      void player.play().catch(() => {
        // Playing right after a download may be refused (iOS): the player's
        // own play button works.
      });
    }
    return () => URL.revokeObjectURL(objectUrl);
  }, [objectUrl]);

  const load = async () => {
    if (isLoading) {
      return;
    }
    setIsLoading(true);
    const result = await loadRecording(callRecordingUrl(business.id, callId));
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

  return (
    <div className="space-y-2">
      {objectUrl ? (
        <audio
          ref={audio}
          controls
          src={objectUrl}
          aria-label={label}
          onError={() => setProblem("failed")}
          onPlaying={() => setProblem(null)}
          className="block h-10 w-full max-w-md"
        >
          {t("conversations.calls.playerUnsupported")}
        </audio>
      ) : problem === null ? (
        <Button
          variant="secondary"
          size="sm"
          aria-label={playLabel}
          aria-busy={isLoading || undefined}
          aria-disabled={isLoading || undefined}
          leadingIcon={busyIcon ?? <IconPlay className="size-4" aria-hidden />}
          onClick={() => void load()}
        >
          {isLoading ? t("conversations.calls.loading") : t("conversations.calls.play")}
        </Button>
      ) : null}
      {problem === "missing" ? <Alert tone="warning">{t("conversations.calls.playMissing")}</Alert> : null}
      {problem === "failed" ? (
        <Alert
          tone="danger"
          action={
            // Not disabled while loading: a disabled button would lose the
            // keyboard focus.
            <Button
              variant="secondary"
              size="sm"
              aria-busy={isLoading || undefined}
              aria-disabled={isLoading || undefined}
              leadingIcon={busyIcon}
              onClick={() => void load()}
            >
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
