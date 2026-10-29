"use client";

/**
 * Times for the person reading the page (see lib/viewerTimeZone): the zone
 * the server rendered with (`aw_tz` cookie) while hydrating, the browser's
 * own right after, and "UTC" with a label before either is known.
 *
 *     const when = useViewerFormat();
 *     when.dateTime(session.last_seen_at)  // "5 окт. 2026 г., 14:05"
 */

import { createContext, useContext, useEffect, useMemo, useSyncExternalStore, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { formatDate, formatDateTime, formatTime, type Timestamp } from "@/lib/format";
import { systemTimeZone } from "@/lib/intl/calendarFields";
import { FALLBACK_TIME_ZONE, viewerTimeZoneCookie } from "@/lib/viewerTimeZone";

const RememberedZoneContext = createContext<string | null>(null);

let deviceZone: string | null | undefined;

/** The device's zone, read once (Intl answers the same for the page's life). */
function currentDeviceZone(): string | null {
  if (deviceZone === undefined) {
    deviceZone = systemTimeZone();
  }
  return deviceZone;
}

const subscribeNever = () => () => undefined;

/** Passes the server's zone down and remembers the device's zone for the next server render. */
export function ViewerTimeZoneProvider({ initialZone, children }: { initialZone: string | null; children: ReactNode }) {
  useEffect(() => {
    const zone = currentDeviceZone();
    if (zone && zone !== initialZone) {
      document.cookie = viewerTimeZoneCookie(zone, window.location.protocol === "https:");
    }
  }, [initialZone]);
  return <RememberedZoneContext.Provider value={initialZone}>{children}</RememberedZoneContext.Provider>;
}

/** The reader's zone, or null while it is unknown (first visit, during hydration). */
function useViewerTimeZone(): string | null {
  const remembered = useContext(RememberedZoneContext);
  return useSyncExternalStore(
    subscribeNever,
    () => currentDeviceZone() ?? remembered,
    () => remembered,
  );
}

type DateStyle = "full" | "long" | "medium" | "short";

export interface ViewerFormat {
  /** The zone the texts are in. */
  timeZone: string;
  dateTime: (value: Timestamp, options?: { dateStyle?: DateStyle }) => string;
  date: (value: Timestamp, options?: { dateStyle?: DateStyle }) => string;
  time: (value: Timestamp) => string;
}

/** Date and time helpers in the reader's zone and the interface language. */
export function useViewerFormat(): ViewerFormat {
  const { locale } = useI18n();
  const known = useViewerTimeZone();
  return useMemo(() => {
    const timeZone = known ?? FALLBACK_TIME_ZONE;
    // A time in the fallback zone says so ("14:05 UTC"); it lasts until hydration ends.
    const labelled = (text: string) => (known ? text : `${text} ${FALLBACK_TIME_ZONE}`);
    return {
      timeZone,
      dateTime: (value, options) => labelled(formatDateTime(value, { locale, timeZone, ...options })),
      date: (value, options) => formatDate(value, { locale, timeZone, ...options }),
      time: (value) => labelled(formatTime(value, { locale, timeZone })),
    };
  }, [known, locale]);
}
