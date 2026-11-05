"use client";

import Link from "next/link";

import { usePlatformStatus } from "@/components/help/usePlatformStatus";
import { IconAlert, IconCheckCircle, IconClock } from "@/components/icons";
import { useViewerFormat } from "@/components/time/ViewerTimeZone";
import { Card, PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import type { PlatformStatus } from "@/lib/help/platformStatus";
import { HOME_PATH } from "@/lib/navigation";

import { AnnouncementCard } from "./AnnouncementCard";
import { ComponentRow } from "./ComponentRow";
import { MonitoringDelayedNotice } from "./MonitoringDelayedNotice";

const OVERALL_FRAMES: Record<PlatformStatus["level"], string> = {
  operational: "border-success/30 bg-success-soft",
  maintenance: "border-info/30 bg-info-soft",
  degraded: "border-warning/40 bg-warning-soft",
  outage: "border-danger/40 bg-danger-soft",
  no_data: "border-line bg-surface",
};

/** The public status page; `initial` is what the server read (null: it could not reach the API). */
export function StatusScreen({ initial }: { initial: PlatformStatus | null }) {
  const { t } = useI18n();
  const viewer = useViewerFormat();
  const query = usePlatformStatus(initial);
  const status = query.data;

  return (
    <div className="space-y-8">
      <PageHeader title={t("platformStatus.title")} description={t("platformStatus.description")} />

      {!status ? (
        <Card>
          <div role="alert" className="flex gap-3">
            <IconAlert className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden />
            <div className="space-y-1">
              <p className="font-semibold text-ink">{t("platformStatus.unreachable.title")}</p>
              <p className="text-sm text-ink-muted">{t("platformStatus.unreachable.body")}</p>
            </div>
          </div>
        </Card>
      ) : (
        <>
          <section
            aria-labelledby="status-overall"
            className={cn("flex items-center gap-4 rounded-2xl border p-5", OVERALL_FRAMES[status.level])}
          >
            {status.level === "operational" ? (
              <IconCheckCircle className="size-8 shrink-0 text-success" aria-hidden />
            ) : status.level === "no_data" ? (
              <IconClock className="size-8 shrink-0 text-ink-subtle" aria-hidden />
            ) : (
              <IconAlert className={cn("size-8 shrink-0", status.level === "outage" ? "text-danger" : "text-warning")} aria-hidden />
            )}
            <div className="min-w-0 space-y-0.5">
              <h2 id="status-overall" className="text-lg font-semibold text-ink" aria-live="polite">
                {t(`platformStatus.overall.${status.level}`)}
              </h2>
              {status.checked_at && !status.monitoring_delayed ? (
                <p className="text-sm text-ink-muted">
                  {t("platformStatus.checkedAt", { time: viewer.dateTime(status.checked_at) })}
                </p>
              ) : null}
            </div>
          </section>

          {status.monitoring_delayed && status.checked_at ? <MonitoringDelayedNotice checkedAt={status.checked_at} /> : null}

          {status.announcements.length > 0 ? (
            <section aria-labelledby="status-now" className="space-y-3">
              <h2 id="status-now" className="text-base font-semibold text-ink">
                {t("platformStatus.activeTitle")}
              </h2>
              {status.announcements.map((announcement) => (
                <AnnouncementCard key={announcement.id} announcement={announcement} />
              ))}
            </section>
          ) : null}

          <Card title={t("platformStatus.componentsTitle")} padded={false}>
            <ul className="divide-y divide-line">
              {status.components.map((component) => (
                <ComponentRow key={component.component} component={component} />
              ))}
            </ul>
          </Card>

          <section aria-labelledby="status-past" className="space-y-3">
            <h2 id="status-past" className="text-base font-semibold text-ink">
              {t("platformStatus.pastTitle")}
            </h2>
            {status.past_announcements.length === 0 ? (
              <p className="text-sm text-ink-muted">{t("platformStatus.pastEmpty")}</p>
            ) : (
              status.past_announcements.map((announcement) => <AnnouncementCard key={announcement.id} announcement={announcement} />)
            )}
          </section>
        </>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5 text-sm text-ink-muted">
        <p>{t("platformStatus.selfMeasured")}</p>
        <Link href={HOME_PATH} className="font-medium text-accent hover:underline">
          {t("platformStatus.openCabinet")}
        </Link>
      </footer>
    </div>
  );
}
