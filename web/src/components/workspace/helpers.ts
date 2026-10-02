/**
 * Pure helpers shared by the channels, billing, settings and admin pages.
 */

/** A URL hash without the leading "#", percent-decoded; "" when its escapes are malformed (e.g. "#%"). */
export function decodeHash(hash: string): string {
  const raw = hash.replace(/^#/, "");
  try {
    return decodeURIComponent(raw);
  } catch {
    return "";
  }
}

/** The owner is warned when a package is used to this share (concept section 9). */
export const USAGE_WARNING_PERCENT = 80;

export type UsageLevel = "none" | "ok" | "warning" | "exceeded";

/**
 * How full a package is: "none" for a package of zero (no percent),
 * "warning" from 80 %, "exceeded" from 100 %.
 */
export function usageLevel(percent: number | null | undefined): UsageLevel {
  if (percent === null || percent === undefined || !Number.isFinite(percent)) {
    return "none";
  }
  if (percent >= 100) {
    return "exceeded";
  }
  return percent >= USAGE_WARNING_PERCENT ? "warning" : "ok";
}

/** Used share of a package in whole percent (rounded down), or null for a package of zero. */
export function usagePercent(used: number, included: number): number | null {
  if (included <= 0) {
    return null;
  }
  return Math.floor((Math.max(used, 0) * 100) / included);
}

/** Width of a usage bar in percent, 0..100. */
export function usageBarWidth(percent: number | null | undefined): number {
  if (percent === null || percent === undefined || !Number.isFinite(percent)) {
    return 0;
  }
  return Math.min(100, Math.max(0, percent));
}

/** Provider costs come in micro US dollars: 1_234_567 -> "$1.2346". */
export function formatMicroUsd(microUsd: number, locale: string): string {
  const dollars = microUsd / 1_000_000;
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: Math.abs(dollars) < 10 ? 4 : 2,
  }).format(dollars);
}

/**
 * The short, recognisable part of a prefixed id:
 * "contact_639833a1-4f05-440f-bbab-540dca7ac3b8" -> "639833a1".
 */
export function shortId(id: string): string {
  const separator = id.lastIndexOf("_");
  const body = separator >= 0 ? id.slice(separator + 1) : id;
  return body.split("-")[0]?.slice(0, 12) || body;
}

/** "2026-10-01" in UTC for file names. */
export function isoDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** A file name safe on every system: letters, digits, dots, dashes and underscores. */
export function safeFileName(name: string): string {
  const cleaned = name
    .normalize("NFKD")
    .replace(/[^\w.-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return cleaned || "download";
}

/** Save JSON as a file in the browser. */
export function downloadJson(data: unknown, fileName: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = safeFileName(fileName);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}

/** Offset of a time zone from UTC at an instant, in milliseconds (Tbilisi: +4 h). */
function zoneOffsetMs(instantMs: number, timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(new Date(instantMs));
  const part = (type: Intl.DateTimeFormatPartTypes) => Number(parts.find((item) => item.type === type)?.value ?? 0);
  const asUtc = Date.UTC(part("year"), part("month") - 1, part("day"), part("hour"), part("minute"), part("second"));
  return asUtc - Math.floor(instantMs / 1000) * 1000;
}

const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * The first moment of a local calendar day ("2026-10-01") in a time zone, as
 * UNIX microseconds (the API's timestamps); null for text that is not a day.
 *
 * Clock changes happen at most once around a midnight, so the offsets a day
 * before and a day after bracket it. Local midnight is the earliest instant
 * that one of them maps to it exactly; where clocks jump over midnight
 * (Santiago, Havana) the day starts at the jump.
 */
export function zonedDayStartUs(day: string, timeZone: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day);
  if (!match) {
    return null;
  }
  const midnightUtc = Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  if (Number.isNaN(midnightUtc)) {
    return null;
  }
  const offsetBefore = zoneOffsetMs(midnightUtc - DAY_MS, timeZone);
  const offsetAfter = zoneOffsetMs(midnightUtc + DAY_MS, timeZone);
  const exact = [offsetBefore, offsetAfter]
    .map((offset) => midnightUtc - offset)
    .filter((instant) => midnightUtc - zoneOffsetMs(instant, timeZone) === instant);
  const instant = exact.length > 0 ? Math.min(...exact) : midnightUtc - offsetBefore;
  return instant * 1000;
}
