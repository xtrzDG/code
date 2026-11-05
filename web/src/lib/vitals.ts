/**
 * Core Web Vitals of the cabinet's pages as telemetry reports: LCP and INP
 * in whole milliseconds, CLS in ten-thousandths (0.1 is 1000), the page as
 * its route template (`/b/[businessId]/inbox`, never an id, a slug or a
 * query, so a measurement names no business or customer) and the device
 * class by viewport width. Only pages behind sign-in report: the API takes
 * telemetry from signed-in people only.
 */

import { isProtectedPath } from "./navigation";
import type { WebVitalReport } from "./track";

type VitalName = WebVitalReport["metric"];
export type DeviceClass = WebVitalReport["device_class"];

const REPORTED: Readonly<Record<string, VitalName>> = { LCP: "lcp", INP: "inp", CLS: "cls" };
/** The API's ceiling for a vital (ten minutes in milliseconds). */
const MAX_VALUE = 600_000;
const CLS_SCALE = 10_000;
/** Tailwind's `sm` and `lg`: below `lg` the sidebar is a drawer. */
const TABLET_MIN_WIDTH = 640;
const DESKTOP_MIN_WIDTH = 1024;
const ROUTE_PATTERN = /^\/[A-Za-z0-9_\-[\]/.]*$/;
const MAX_ROUTE_LENGTH = 160;

export function deviceClassOf(viewportWidth: number): DeviceClass {
  if (viewportWidth < TABLET_MIN_WIDTH) {
    return "mobile";
  }
  return viewportWidth < DESKTOP_MIN_WIDTH ? "tablet" : "desktop";
}

/**
 * The route template of a cabinet path; null when it cannot be one (then
 * nothing is reported). Dynamic segments are those of src/app.
 */
export function routeTemplate(pathname: string): string | null {
  const segments = pathname.split("/").filter((segment) => segment !== "");
  const [first, second, third, fourth] = segments;
  if (first === "b" && second !== undefined) {
    segments[1] = "[businessId]";
    if (third === "inbox" && fourth !== undefined) {
      segments[3] = "[conversationId]";
    } else if (third === "assistant" && fourth === "versions" && segments[4] !== undefined) {
      segments[4] = "[versionId]";
    }
  } else if (first === "admin" && second === "clients" && third !== undefined) {
    segments[2] = "[businessId]";
  } else if (first === "c" && second !== undefined) {
    segments[1] = "[slug]";
  } else if (first === "n" && second !== undefined) {
    segments[1] = "[token]";
  }
  const route = `/${segments.join("/")}`;
  return route.length <= MAX_ROUTE_LENGTH && ROUTE_PATTERN.test(route) ? route : null;
}

/** The report of one measured vital, or null for another vital or page. */
export function vitalReport(
  metric: { name: string; value: number },
  pathname: string,
  viewportWidth: number,
): WebVitalReport | null {
  const name = REPORTED[metric.name];
  const route = isProtectedPath(pathname) ? routeTemplate(pathname) : null;
  if (!name || route === null || !Number.isFinite(metric.value)) {
    return null;
  }
  const scaled = name === "cls" ? metric.value * CLS_SCALE : metric.value;
  return {
    kind: "web_vital",
    metric: name,
    value: Math.min(MAX_VALUE, Math.max(0, Math.round(scaled))),
    route,
    device_class: deviceClassOf(viewportWidth),
  };
}
