"use client";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconAlert, IconCalendar } from "@/components/icons";
import { ButtonLink, Card, EmptyState, Skeleton } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";
import { summaryLine, type ResourceSyncSummary } from "@/lib/resourceCalendar";

/**
 * The resources whose calendars are linked or shared, each with its
 * one-line summary and last read; they are managed on Resources and hours.
 */
export function ResourceCalendarsCard({
  summaries,
  resourceName,
}: {
  summaries: readonly ResourceSyncSummary[];
  /** The resource's name; undefined while names load, null once it is gone. */
  resourceName: (resourceId: string) => string | null | undefined;
}) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const resourcesPath = `${businessPath(business.id, "assistant/knowledge")}/resources`;
  return (
    <Card
      padded={false}
      title={t("calendarSync.integrations.resourcesTitle")}
      actions={
        <ButtonLink href={resourcesPath} variant="secondary" size="sm">
          {t("calendarSync.integrations.manage")}
        </ButtonLink>
      }
    >
      {summaries.length === 0 ? (
        <EmptyState icon={<IconCalendar className="size-6" />} title={t("calendarSync.integrations.noResources")} />
      ) : (
        <ul className="divide-y divide-line">
          {summaries.map((summary) => {
            const line = summaryLine(summary);
            const name = resourceName(summary.resource_id);
            return (
              <li key={summary.resource_id} className="space-y-0.5 px-4 py-3 sm:px-6">
                {name === undefined ? (
                  <Skeleton className="h-5 w-40" />
                ) : name === null ? (
                  <p className="font-medium text-ink-muted">{t("calendarSync.integrations.removedResource")}</p>
                ) : (
                  <p className="font-medium text-ink" dir="auto" data-user-content>
                    {name}
                  </p>
                )}
                {line ? (
                  <p className={line.tone === "warning" ? "flex items-center gap-1.5 text-sm text-warning" : "text-sm text-ink-subtle"}>
                    {line.tone === "warning" ? <IconAlert className="size-4 shrink-0" aria-hidden /> : null}
                    {line.count === undefined ? t(line.key) : tp(line.key, line.count)}
                  </p>
                ) : null}
                {summary.last_synced_at ? (
                  <p className="text-sm text-ink-subtle">
                    {t("calendarSync.integrations.lastSynced", { time: format.dateTime(summary.last_synced_at) })}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
