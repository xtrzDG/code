"use client";

import { IconClock, IconTrash } from "@/components/icons";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatLocalDate, intervalsLabel, type ScheduleExceptionView } from "@/lib/specialDays";

/** One holiday or special-hours day: the date, closed or its hours, what it applies to, and delete. */
export function ExceptionRow({
  exception,
  isPast,
  appliesTo,
  onDelete,
}: {
  exception: ScheduleExceptionView;
  isPast: boolean;
  /** The resource it applies to, or null for the whole business. */
  appliesTo: string | null;
  onDelete: (exception: ScheduleExceptionView) => void;
}) {
  const { t, locale } = useI18n();
  return (
    <li className="flex flex-col gap-2 px-4 py-4 sm:flex-row sm:items-start sm:gap-6 sm:px-6">
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className={isPast ? "font-medium text-ink-muted" : "font-medium text-ink"}>{formatLocalDate(exception.date, locale)}</p>
          {exception.is_closed_all_day ? (
            <Badge tone="danger">{t("knowledge.exceptions.closed")}</Badge>
          ) : (
            <Badge tone="info" icon={<IconClock className="size-3.5" aria-hidden />}>
              {intervalsLabel(exception.special_hours ?? [])}
            </Badge>
          )}
        </div>
        <p className="text-sm text-ink-subtle">{appliesTo ?? t("knowledge.exceptions.wholeBusiness")}</p>
        {exception.note ? (
          <p className="text-sm break-words text-ink-muted" dir="auto">
            {exception.note}
          </p>
        ) : null}
      </div>
      <Button
        variant="ghost"
        size="sm"
        className="self-start hover:text-danger"
        leadingIcon={<IconTrash className="size-4" aria-hidden />}
        aria-label={`${t("common.delete")}: ${formatLocalDate(exception.date, locale)}`}
        onClick={() => onDelete(exception)}
      >
        {t("common.delete")}
      </Button>
    </li>
  );
}
