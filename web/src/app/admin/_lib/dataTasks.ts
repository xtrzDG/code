import type { Schema } from "@/api/types";

/** The post-deploy data tasks as GET /v1/admin/system/data-tasks answers them. */
export type DataTasksView = Schema<"DataTasksView">;
export type DataTask = Schema<"DataTaskView">;
export type DataTaskStatus = DataTask["status"];

/** The card looks again every 30 seconds, like the rest of the page. */
export const DATA_TASKS_POLL_MS = 30_000;

/** Failed tasks first (they need a person), then the running and the waiting ones. */
const OPEN_ORDER: Readonly<Record<DataTaskStatus, number>> = { failed: 0, running: 1, pending: 2, done: 3 };

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

/**
 * The open tasks (failed, then running, then waiting; the registry's order
 * within each) and the done ones: the card lists the open ones and folds
 * the done ones away, since after a settled deploy nearly every task is done.
 */
export function splitDataTasks(tasks: readonly DataTask[]): { open: DataTask[]; done: DataTask[] } {
  const open = tasks
    .filter((task) => task.status !== "done")
    .sort((first, second) => OPEN_ORDER[first.status] - OPEN_ORDER[second.status]);
  return { open, done: tasks.filter((task) => task.status === "done") };
}
