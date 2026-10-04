"use client";

import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { formatDateTime, formatNumber } from "@/lib/format";

import { byteSize, durationParts, type AlertState, type AlertUnit, type JobLane, type RunState } from "../../_lib/system";

export const LANE_NAMES: Readonly<Record<JobLane, MessageKey>> = {
  inbound: "adminSystem.lanes.names.inbound",
  outbound: "adminSystem.lanes.names.outbound",
  default: "adminSystem.lanes.names.default",
  autotests: "adminSystem.lanes.names.autotests",
};

export const RUN_STATE_NAMES: Readonly<Record<RunState, MessageKey>> = {
  ok: "adminSystem.backups.states.ok",
  failed: "adminSystem.backups.states.failed",
  overdue: "adminSystem.backups.states.overdue",
  missing: "adminSystem.backups.states.missing",
};

/** Times, durations, sizes and alert figures of the System page in the interface language (lib/format.ts, lib/intl). */
export function useSystemFormat() {
  const { t, tp, locale } = useI18n();
  const number = (value: number) => formatNumber(value, locale);
  const duration = (seconds: number) => {
    const { unit, count } = durationParts(seconds);
    return tp(`adminSystem.duration.${unit}`, count);
  };
  const figure = (value: number, unit: AlertUnit) => {
    if (unit === "seconds") {
      return duration(value);
    }
    if (unit === "percent") {
      return formatNumber(value / 100, locale, { style: "percent", maximumFractionDigits: 0 });
    }
    // Counts, and the handoff spike's hourly counts.
    return number(value);
  };
  return {
    number,
    duration,
    /** "12 min ago". */
    ago: (seconds: number) => t("adminSystem.ago", { duration: duration(seconds) }),
    /** An API time (microseconds) in the admin's own time zone; "—" without one. */
    when: (micros: number | null | undefined) => (micros ? formatDateTime(micros, { locale }) : "—"),
    bytes: (bytes: number) => {
      const { unit, value } = byteSize(bytes);
      return t(`adminSystem.bytes.${unit}`, { value: formatNumber(value, locale, { maximumFractionDigits: 1 }) });
    },
    /** "Now 7%, fires above 5%". */
    alertFigure: (alert: Pick<AlertState, "figure" | "threshold" | "unit">) =>
      t("adminSystem.alerts.figure", { figure: figure(alert.figure, alert.unit), threshold: figure(alert.threshold, alert.unit) }),
  };
}

export type SystemFormat = ReturnType<typeof useSystemFormat>;
