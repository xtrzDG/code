/**
 * The platform's health (GET /v1/admin/system) as the System page reads it:
 * which alerts fire, which lanes fall behind, how the backups stand, and
 * the sizes and durations in units a person reads at a glance. Pure
 * functions, so the page and the tests share them.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

export type AdminSystem = Schema<"AdminSystemView">;
export type AlertState = Schema<"AlertStateView">;
export type AlertUnit = Schema<"AlertUnit">;
export type IncidentSeverity = Schema<"IncidentSeverity">;
export type JobLane = Schema<"JobLane">;
export type Lane = Schema<"LaneView">;
export type WorkerPulse = Schema<"WorkerPulseView">;
export type ChannelIssue = Schema<"ChannelIssueView">;
export type TableSize = Schema<"TableSizeView">;
export type MaintenanceRun = Schema<"MaintenanceRunView">;
export type QueuedJob = Schema<"QueuedJobView">;

/** The page looks again this often while it is visible (the alerts job itself runs every five minutes). */
export const SYSTEM_POLL_MS = 30_000;

/** A lane whose oldest due job waited longer than this is behind: the `inbound_backlog` alert's threshold. */
const LANE_BEHIND_SECONDS = 120;

/** The restore drill runs weekly (docs/operations/backup-restore.md); a day of slack before it counts as late. */
const DRILL_OVERDUE_DAYS = 8;

/** The largest tables shown; the rest are in the total. */
const TABLES_SHOWN = 8;

const MICROSECONDS_PER_DAY = 24 * 60 * 60 * 1_000_000;

export const SEVERITY_TONES: Readonly<Record<IncidentSeverity, BadgeTone>> = {
  sev1: "danger",
  sev2: "warning",
  sev3: "info",
};

const SEVERITY_RANK: Readonly<Record<IncidentSeverity, number>> = { sev1: 0, sev2: 1, sev3: 2 };

export interface AlertGroups {
  /** Most severe first, then the longest firing. */
  firing: AlertState[];
  /** The most recently resolved first. */
  resolved: AlertState[];
}

export function groupAlerts(alerts: readonly AlertState[]): AlertGroups {
  const firing = alerts
    .filter((alert) => alert.status === "firing")
    .sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] || a.fired_at - b.fired_at);
  const resolved = alerts
    .filter((alert) => alert.status === "resolved")
    .sort((a, b) => (b.resolved_at ?? 0) - (a.resolved_at ?? 0));
  return { firing, resolved };
}

type DurationUnit = "seconds" | "minutes" | "hours" | "days";

export interface DurationParts {
  unit: DurationUnit;
  count: number;
}

/** "45 s", "12 min", "5 h", "3 days": the largest unit that still reads exactly enough, rounded down. */
export function durationParts(seconds: number): DurationParts {
  const whole = Math.max(0, Math.floor(seconds));
  if (whole < 120) {
    return { unit: "seconds", count: whole };
  }
  if (whole < 120 * 60) {
    return { unit: "minutes", count: Math.floor(whole / 60) };
  }
  if (whole < 48 * 60 * 60) {
    return { unit: "hours", count: Math.floor(whole / 3600) };
  }
  return { unit: "days", count: Math.floor(whole / 86_400) };
}

type ByteUnit = "b" | "kb" | "mb" | "gb" | "tb";

export interface ByteSize {
  unit: ByteUnit;
  value: number;
}

const BYTE_UNITS: readonly ByteUnit[] = ["b", "kb", "mb", "gb", "tb"];

/** Binary multiples (1 KB = 1024 bytes), with one decimal under 10: "4.2 GB", "37 MB", "812 B". */
export function byteSize(bytes: number): ByteSize {
  let value = Math.max(0, bytes);
  let index = 0;
  while (value >= 1024 && index < BYTE_UNITS.length - 1) {
    value /= 1024;
    index += 1;
  }
  let rounded = index === 0 || value >= 10 ? Math.round(value) : Math.round(value * 10) / 10;
  if (rounded >= 1024 && index < BYTE_UNITS.length - 1) {
    rounded = 1;
    index += 1;
  }
  return { unit: BYTE_UNITS[index] ?? "b", value: rounded };
}

/** The tables that hold the most, biggest first. */
export function largestTables(tables: readonly TableSize[], limit = TABLES_SHOWN): TableSize[] {
  return [...tables].sort((a, b) => b.total_bytes - a.total_bytes || a.table.localeCompare(b.table)).slice(0, limit);
}

/** "workshop.messages" → "messages": every table lives in the one schema. */
export function tableName(table: string): string {
  const dot = table.indexOf(".");
  return dot === -1 ? table : table.slice(dot + 1);
}

function isLaneBehind(lane: Lane): boolean {
  return (lane.oldest_wait_seconds ?? 0) > LANE_BEHIND_SECONDS;
}

/** The tone of a lane's row: dead jobs first, then a backlog. */
export function laneTone(lane: Lane): BadgeTone | null {
  if (lane.dead > 0) {
    return "danger";
  }
  return isLaneBehind(lane) ? "warning" : null;
}

/** How a backup or a restore drill stands: none yet, the last one failed, too long ago, or fine. */
export type RunState = "missing" | "failed" | "overdue" | "ok";

export const RUN_STATE_TONES: Readonly<Record<RunState, BadgeTone>> = {
  missing: "warning",
  failed: "danger",
  overdue: "warning",
  ok: "success",
};

export function backupState(system: Pick<AdminSystem, "last_backup" | "is_backup_overdue">): RunState {
  const run = system.last_backup;
  if (!run) {
    return "missing";
  }
  if (run.outcome === "failed") {
    return "failed";
  }
  return system.is_backup_overdue ? "overdue" : "ok";
}

export function drillState(system: Pick<AdminSystem, "last_restore_drill" | "checked_at">): RunState {
  const run = system.last_restore_drill;
  if (!run) {
    return "missing";
  }
  if (run.outcome === "failed") {
    return "failed";
  }
  return system.checked_at - run.finished_at > DRILL_OVERDUE_DAYS * MICROSECONDS_PER_DAY ? "overdue" : "ok";
}

/** Workers that stopped beating first, then by host. */
export function sortWorkers(workers: readonly WorkerPulse[]): WorkerPulse[] {
  return [...workers].sort((a, b) => Number(b.is_stale) - Number(a.is_stale) || a.host_name.localeCompare(b.host_name));
}

/** How many things want a look now: firing alerts, stale workers, dead jobs, channels in error. */
export function attentionCount(system: AdminSystem): number {
  const deadJobs = system.dead_jobs.reduce((total, tally) => total + tally.count, 0);
  return (
    system.alerts.filter((alert) => alert.status === "firing").length +
    system.workers.filter((worker) => worker.is_stale).length +
    deadJobs +
    system.channels_in_error_count
  );
}
