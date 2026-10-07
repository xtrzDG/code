/**
 * How the calendar draws bookings and hours, from the design tokens only:
 * a booking's colour says its status (ochre waits, olive is confirmed,
 * graphite is done, brick did not come), closed hours are hatched.
 */

import type { CSSProperties } from "react";

import type { BookingStatus } from "@/components/insights/types";

export const STATUS_STYLE: Record<BookingStatus, { block: string; mark: string }> = {
  pending: { block: "border-warning/45 bg-warning-soft", mark: "bg-warning" },
  confirmed: { block: "border-success/40 bg-success-soft", mark: "bg-success" },
  completed: { block: "border-line-strong/40 bg-surface-muted", mark: "bg-line-strong" },
  no_show: { block: "border-danger/40 bg-danger-soft", mark: "bg-danger" },
  cancelled: { block: "border-line bg-surface-muted", mark: "bg-line" },
};

/** The statuses the calendar shows (a cancelled booking frees its place and leaves the grid). */
export const SHOWN_STATUSES: readonly BookingStatus[] = ["pending", "confirmed", "completed", "no_show"];

/** Closed hours and nights: a quiet hatch over the muted surface. */
export const CLOSED_STYLE: CSSProperties = {
  backgroundImage: "repeating-linear-gradient(135deg, var(--line) 0 1px, transparent 1px 8px)",
};

/** Where the moved booking would land: a dashed clay outline. */
export const GHOST_CLASS = "pointer-events-none border-2 border-dashed border-accent-solid bg-accent-soft text-accent-ink";
