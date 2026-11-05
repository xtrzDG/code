"use client";

/**
 * A time zone as a screen names it: its city, then its UTC offset now
 * ("Berlin (UTC+1)", timeZones.ts). The offset depends on the moment (summer
 * time), and the server renders at its own moment: around a change of the
 * clocks, or in a test whose browser clock is set to another day, the server's
 * HTML and the browser's first render would name different offsets and break
 * hydration (React error #418). So the server's HTML and the hydrating render
 * name the city alone, and the offset follows once the page has hydrated; a
 * component first rendered in the browser names it at once.
 */

import { useCallback } from "react";

import { useHydrated } from "@/lib/csp/clientStyle";
import { timeZoneLabel, zoneCity } from "@/lib/timeZones";

export function useTimeZoneLabel(locale: string): (zone: string) => string {
  const hydrated = useHydrated();
  return useCallback((zone: string) => (hydrated ? timeZoneLabel(zone, locale) : zoneCity(zone, locale)), [hydrated, locale]);
}
