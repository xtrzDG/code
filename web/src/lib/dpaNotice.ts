/**
 * The notice of a new data processing agreement (components/shell/
 * DpaBanner.tsx): shown to owners of a business that accepted an earlier
 * version and not the one in force, with the day it is due (30 days after
 * the version's date) and whether that day has passed.
 */

import type { Schema } from "@/api/types";

export type DpaStatus = Schema<"DpaStatusView">;

export interface DpaReacceptance {
  version: string;
  /** "2026-11-05": the last day to accept. */
  dueOn: string;
  isOverdue: boolean;
}

/** What the banner says, or null when there is nothing to accept again. `today` is "YYYY-MM-DD". */
export function dpaReacceptance(view: DpaStatus | undefined, today: string): DpaReacceptance | null {
  if (!view || !view.needs_reacceptance || view.is_current_version_accepted || !view.acceptance_due_on) {
    return null;
  }
  return {
    version: view.current_document_version,
    dueOn: view.acceptance_due_on,
    isOverdue: today > view.acceptance_due_on,
  };
}

/** A calendar day ("2026-11-05") as a moment that is that day in UTC, to format with timeZone "UTC". */
export function calendarDayMoment(day: string): Date {
  return new Date(`${day}T12:00:00Z`);
}
