"use client";

import { useEffect, useState } from "react";

import { IconClock } from "@/components/icons";
import { useViewerFormat } from "@/components/time/ViewerTimeZone";
import { useIsClient } from "@/components/workspace/useIsClient";
import { useI18n } from "@/i18n/client";
import { minutesSinceCheck } from "@/lib/help/platformStatus";

/** How often the "N min ago" line counts on while the page is open. */
const TICK_MS = 30_000;

/** The browser's clock, ticking; read only after hydration (the server's would differ). */
function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), TICK_MS);
    return () => window.clearInterval(timer);
  }, []);
  return now;
}

/**
 * The platform's own checks are late (`monitoring_delayed`): nobody can
 * vouch for the levels below, so the page says when it last looked ("last
 * check 17 min ago") instead of an "everything works" nobody measured.
 * Before hydration it names the time of the check (the server's clock is
 * not the reader's).
 */
export function MonitoringDelayedNotice({ checkedAt }: { checkedAt: number }) {
  const { t, tp } = useI18n();
  const viewer = useViewerFormat();
  const isClient = useIsClient();
  const now = useNow();
  const lastCheck = isClient
    ? tp("platformStatus.monitoringDelayed.minutesAgo", minutesSinceCheck(checkedAt, now))
    : t("platformStatus.monitoringDelayed.at", { time: viewer.dateTime(checkedAt) });

  return (
    <div role="status" className="flex gap-3 rounded-2xl border border-warning/40 bg-warning-soft p-4">
      <IconClock className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden />
      <div className="min-w-0 space-y-1 text-sm">
        <p className="font-semibold text-ink">{t("platformStatus.monitoringDelayed.title")}</p>
        <p className="text-ink-muted">{lastCheck}</p>
        <p className="text-ink-muted">{t("platformStatus.monitoringDelayed.body")}</p>
      </div>
    </div>
  );
}
