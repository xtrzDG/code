"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { UserContent } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { busyRange, type BusyTimeView } from "@/lib/resourceCalendar";

import { CalendarSection } from "./CalendarParts";

const SOURCE_LABELS: Readonly<Record<BusyTimeView["source"], MessageKey>> = {
  google: "calendarSync.busy.sources.google",
  ical: "calendarSync.busy.sources.ical",
  booking_system: "calendarSync.busy.sources.booking_system",
};

/** The busy times ahead that the calendars gave, with where each came from (never what it is). */
export function BusyTimesList({ blocks }: { blocks: readonly BusyTimeView[] }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  return (
    <CalendarSection title={t("calendarSync.busy.title")}>
      {blocks.length === 0 ? (
        <p className="text-sm text-ink-subtle">{t("calendarSync.busy.empty")}</p>
      ) : (
        <ul className="space-y-1.5">
          {blocks.map((block) => (
            <li
              key={`${block.source}-${block.feed_host ?? ""}-${block.starts_at}`}
              className="flex flex-col gap-0.5 text-sm sm:flex-row sm:items-baseline sm:justify-between sm:gap-3"
            >
              <span className="text-ink tabular-nums">{busyRange(block, format)}</span>
              <span className="truncate text-ink-subtle">
                {t(SOURCE_LABELS[block.source])}
                {block.feed_host ? (
                  <>
                    {" · "}
                    <UserContent dir="ltr">{block.feed_host}</UserContent>
                  </>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      )}
    </CalendarSection>
  );
}
