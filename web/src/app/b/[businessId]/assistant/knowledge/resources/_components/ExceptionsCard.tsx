"use client";

import { useState } from "react";

import type { Query } from "@/api/useQuery";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCalendar, IconPlus } from "@/components/icons";
import { Button, Card, EmptyState, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { ScheduleExceptionView } from "@/lib/specialDays";

import { ExceptionRow } from "./ExceptionRow";

/** Holidays and special-hours days: the upcoming ones, and the past ones on request. */
export function ExceptionsCard({
  exceptions,
  upcoming,
  past,
  resourceName,
  onAdd,
  onDelete,
}: {
  exceptions: Pick<Query<{ items?: ScheduleExceptionView[] }>, "data" | "error" | "isLoading" | "reload">;
  upcoming: ScheduleExceptionView[];
  past: ScheduleExceptionView[];
  resourceName: (id: string | null | undefined) => string | null;
  onAdd: () => void;
  onDelete: (exception: ScheduleExceptionView) => void;
}) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const [showPast, setShowPast] = useState(false);
  const row = (exception: ScheduleExceptionView, isPast: boolean) => (
    <ExceptionRow key={exception.id} exception={exception} isPast={isPast} appliesTo={resourceName(exception.resource_id)} onDelete={onDelete} />
  );

  return (
    <Card
      padded={false}
      title={t("knowledge.exceptions.title")}
      description={t("knowledge.exceptions.description", { timezone: format.timeZone })}
      actions={
        <Button size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={onAdd}>
          {t("knowledge.exceptions.add")}
        </Button>
      }
    >
      {exceptions.isLoading && !exceptions.data ? (
        <LoadingRegion label={t("common.loading")} className="p-5">
          <SkeletonText lines={3} />
        </LoadingRegion>
      ) : exceptions.error && !exceptions.data ? (
        <ErrorState error={exceptions.error} onRetry={exceptions.reload} />
      ) : upcoming.length === 0 && past.length === 0 ? (
        <EmptyState
          icon={<IconCalendar className="size-6" />}
          title={t("knowledge.exceptions.emptyTitle")}
          description={t("knowledge.exceptions.emptyDescription")}
        />
      ) : (
        <>
          {upcoming.length === 0 ? (
            <p className="px-4 py-6 text-sm text-ink-muted sm:px-6">{t("knowledge.exceptions.noUpcoming")}</p>
          ) : (
            <ul className="divide-y divide-line">{upcoming.map((exception) => row(exception, false))}</ul>
          )}
          {past.length > 0 ? (
            <div className="border-t border-line">
              <div className="px-4 py-3 sm:px-6">
                <Button variant="ghost" size="sm" aria-expanded={showPast} onClick={() => setShowPast((value) => !value)}>
                  {showPast ? t("knowledge.exceptions.hidePast") : t("knowledge.exceptions.showPast", { count: past.length })}
                </Button>
              </div>
              {showPast ? <ul className="divide-y divide-line border-t border-line">{past.map((exception) => row(exception, true))}</ul> : null}
            </div>
          ) : null}
        </>
      )}
    </Card>
  );
}
