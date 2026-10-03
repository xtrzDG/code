"use client";

/**
 * Where the Refresh button used to be: whether the page is live and how
 * fresh its data is ("Live · Updated just now"). Lists reload by
 * themselves when the live stream reports a change; while the connection
 * is down the dot turns amber and "Try now" reconnects at once.
 */

import { useEffect, useState } from "react";

import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { formatTime } from "@/lib/format";
import { freshness } from "@/lib/freshness";

import { useLiveCabinet } from "./LiveEvents";

const TICK_MS = 30_000;

function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), TICK_MS);
    return () => window.clearInterval(timer);
  }, []);
  return now;
}

function UpdatedText({ updatedAt, isFetching }: { updatedAt: number; isFetching: boolean }) {
  const { t, tp, locale } = useI18n();
  const now = useNow();
  if (isFetching && updatedAt > 0) {
    return <>{t("live.updating")}</>;
  }
  const state = freshness(updatedAt, Math.max(now, updatedAt));
  switch (state.kind) {
    case "never":
      return null;
    case "justNow":
      return <>{t("live.updatedJustNow")}</>;
    case "minutes":
      return <>{tp("live.updatedMinutesAgo", state.minutes)}</>;
    case "at":
      return <>{t("live.updatedAt", { time: formatTime(state.at, { locale }) })}</>;
  }
}

export function LiveStatus({
  updatedAt,
  isFetching = false,
  className,
}: {
  /** When the page's data came from the server (ms; 0 while loading). */
  updatedAt: number;
  isFetching?: boolean;
  className?: string;
}) {
  const { t } = useI18n();
  const live = useLiveCabinet();
  const status = live?.status ?? null;
  const isLive = status === "live";
  const isDown = status === "reconnecting" || status === "stopped";

  return (
    <div className={cn("flex min-h-9 flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-subtle", className)}>
      {status ? (
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-medium",
            isLive ? "border-success/30 bg-success-soft text-success" : "border-line bg-surface-muted text-ink-muted",
          )}
          title={isLive ? t("live.liveHint") : isDown ? t("live.reconnectingHint") : undefined}
          data-live-status={status}
        >
          <span className="relative inline-flex size-2" aria-hidden>
            {isLive ? <span className="absolute inset-0 rounded-full bg-success opacity-60 motion-safe:animate-ping" /> : null}
            <span className={cn("relative inline-flex size-2 rounded-full", isLive ? "bg-success" : isDown ? "bg-warning" : "bg-ink-subtle")} />
          </span>
          {t(`live.status.${status === "stopped" ? "paused" : status}`)}
        </span>
      ) : null}
      <span className="tabular-nums">
        <UpdatedText updatedAt={updatedAt} isFetching={isFetching} />
      </span>
      {isDown && live ? (
        <button
          type="button"
          onClick={live.reconnect}
          className="rounded-md px-1.5 py-1 font-medium text-accent hover:underline focus-visible:outline-2 focus-visible:outline-focus pointer-coarse:min-h-11"
        >
          {t("live.reconnect")}
        </button>
      ) : null}
    </div>
  );
}
