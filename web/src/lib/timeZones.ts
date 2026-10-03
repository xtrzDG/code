/**
 * Time zones as people name them: "Тбилиси (UTC+4)", "თბილისი (UTC+4)",
 * "New York (UTC−4)" rather than "Asia/Tbilisi (UTC+04:00)". The city
 * comes from the backend's CLDR table (zoneCities.generated: browsers have
 * no Georgian cities), or from the zone's own name; the offset is the one
 * in force at the given moment, so it follows summer time.
 */

import { ZONE_CITIES } from "./zoneCities.generated";

const MINUS = "−";

/** One formatter per zone (a settings list labels a few hundred zones); null for a zone Intl refuses. */
const offsetFormatters = new Map<string, Intl.DateTimeFormat | null>();

function offsetFormatter(zone: string): Intl.DateTimeFormat | null {
  if (!offsetFormatters.has(zone)) {
    try {
      offsetFormatters.set(zone, new Intl.DateTimeFormat("en-US", { timeZone: zone, timeZoneName: "longOffset" }));
    } catch {
      offsetFormatters.set(zone, null);
    }
  }
  return offsetFormatters.get(zone) ?? null;
}

/** Minutes east of UTC at `at` (Tbilisi 240, New York −240 in summer); null for an unknown zone. */
export function utcOffsetMinutes(zone: string, at: Date): number | null {
  const formatter = offsetFormatter(zone);
  if (!formatter) {
    return null;
  }
  const name = formatter.formatToParts(at).find((part) => part.type === "timeZoneName")?.value ?? "";
  if (name === "GMT" || name === "UTC") {
    return 0;
  }
  const match = /^GMT([+-−])(\d{1,2}):?(\d{2})?$/.exec(name);
  if (!match) {
    return null;
  }
  const minutes = Number(match[2]) * 60 + Number(match[3] ?? 0);
  return match[1] === "+" ? minutes : -minutes;
}

/** 240 -> "UTC+4", 330 -> "UTC+5:30", −180 -> "UTC−3", 0 -> "UTC". */
export function formatUtcOffset(minutes: number): string {
  if (minutes === 0) {
    return "UTC";
  }
  const absolute = Math.abs(minutes);
  const hours = Math.floor(absolute / 60);
  const rest = absolute % 60;
  return `UTC${minutes > 0 ? "+" : MINUS}${hours}${rest ? `:${String(rest).padStart(2, "0")}` : ""}`;
}

/** The city that names a zone in the locale: "Asia/Tbilisi" -> "Тбилиси"; the zone's own city otherwise. */
export function zoneCity(zone: string, locale: string): string {
  const language = locale.split(/[-_]/)[0]?.toLowerCase() ?? locale;
  return ZONE_CITIES[language]?.[zone] ?? zone.split("/").at(-1)?.replace(/_/g, " ") ?? zone;
}

/** "Тбилиси (UTC+4)": the zone's city and its offset now (or at `at`). */
export function timeZoneLabel(zone: string, locale: string, at: Date = new Date()): string {
  const offset = utcOffsetMinutes(zone, at);
  const city = zoneCity(zone, locale);
  return offset === null ? city : `${city} (${formatUtcOffset(offset)})`;
}

/** Zones in the order a list shows them: by offset west to east, then by city. */
export function sortZones(zones: readonly string[], locale: string, at: Date = new Date()): string[] {
  const keyed = zones.map((zone) => ({ zone, offset: utcOffsetMinutes(zone, at) ?? 0, city: zoneCity(zone, locale) }));
  keyed.sort((left, right) => left.offset - right.offset || left.city.localeCompare(right.city, locale));
  return keyed.map((item) => item.zone);
}
