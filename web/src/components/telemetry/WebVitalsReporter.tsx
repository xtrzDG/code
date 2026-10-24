"use client";

import { useReportWebVitals } from "next/web-vitals";

import { track } from "@/lib/track";
import { vitalReport } from "@/lib/vitals";

/**
 * Sends LCP, INP and CLS of the signed-in pages to the API (lib/vitals.ts,
 * lib/track.ts). Mounted once by the root layout; renders nothing.
 */
export function WebVitalsReporter() {
  useReportWebVitals((metric) => {
    const report = vitalReport(metric, window.location.pathname, window.innerWidth);
    if (report) {
      track(report);
    }
  });
  return null;
}
