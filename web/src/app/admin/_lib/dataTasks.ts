import type { Schema } from "@/api/types";

/** The post-deploy data tasks as GET /v1/admin/system/data-tasks answers them. */
export type DataTasksView = Schema<"DataTasksView">;
export type DataTask = Schema<"DataTaskView">;
export type DataTaskStatus = DataTask["status"];

/** The card looks again every 30 seconds, like the rest of the page. */
export const DATA_TASKS_POLL_MS = 30_000;

/** What a task fills: `contacts.last_seen_at`, or `contacts` for a migration. */
export function dataTaskTarget(task: Pick<DataTask, "collection_name" | "field">): string {
  return task.field ? `${task.collection_name}.${task.field}` : task.collection_name;
}

/**
 * How far the current walk is, 0–100, against the table's estimated rows;
 * null when the estimate is unknown (or zero: an empty table is done at once).
 * A done task is always complete.
 */
export function dataTaskPercent(task: Pick<DataTask, "status" | "scanned_count" | "row_estimate">): number | null {
  if (task.status === "done") {
    return 100;
  }
  if (!task.row_estimate) {
    return null;
  }
  return Math.min(99, Math.floor((task.scanned_count / task.row_estimate) * 100));
}

/** The badge tone of a status: failed red, open amber, done green. */
export function dataTaskTone(status: DataTaskStatus): "danger" | "warning" | "success" {
  if (status === "failed") {
    return "danger";
  }
  return status === "done" ? "success" : "warning";
}
