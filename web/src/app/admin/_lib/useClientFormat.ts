"use client";

import { useI18n } from "@/i18n/client";
import { formatDate, formatDateTime, formatMoney, type Timestamp } from "@/lib/format";

/** Dates in the client's time zone and money in the interface language. */
export function useClientFormat(timeZone: string) {
  const { locale } = useI18n();
  return {
    date: (value: Timestamp) => formatDate(value, { locale, timeZone }),
    dateTime: (value: Timestamp) => formatDateTime(value, { locale, timeZone }),
    money: (minor: number, currency: string) => formatMoney(minor, currency, locale),
  };
}
