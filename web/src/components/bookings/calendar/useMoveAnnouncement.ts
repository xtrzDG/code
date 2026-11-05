"use client";

import { formatLocalDate, formatLocalTime } from "@/components/insights/dates";
import { useI18n } from "@/i18n/client";

import type { MovePreview } from "./useMoveGestures";

/** What a screen reader hears while a booking is moved with the keys: where it would go, or that it stayed. */
export function useMoveAnnouncement(preview: MovePreview | null, isCancelled: boolean): string {
  const { t, locale } = useI18n();
  if (preview?.source === "keys") {
    const { target } = preview;
    return target.time
      ? t("bookingCalendar.move.pending", { place: target.resourceName, time: formatLocalTime(target.time, locale) })
      : t("bookingCalendar.move.pendingStay", {
          place: target.resourceName,
          date: formatLocalDate(target.date, locale, { day: "numeric", month: "long" }),
        });
  }
  return isCancelled ? t("bookingCalendar.move.cancelled") : "";
}
