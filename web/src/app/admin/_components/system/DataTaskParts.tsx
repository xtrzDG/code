"use client";

import { IconRefresh } from "@/components/icons";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { dataTaskPercent, dataTaskTarget, dataTaskTone, type DataTask, type DataTaskStatus } from "../../_lib/dataTasks";
import { useSystemFormat } from "./useSystemFormat";

/**
 * The pieces of one post-deploy data task, shared by the table of wide
 * screens (DataTaskRows) and the stacked list of phones (DataTaskItems).
 */

const STATUS_NAMES: Readonly<Record<DataTaskStatus, MessageKey>> = {
  pending: "dataTasks.statuses.pending",
  running: "dataTasks.statuses.running",
  done: "dataTasks.statuses.done",
  failed: "dataTasks.statuses.failed",
};
const LIST_NAMES: Readonly<Record<DataTask["lists"][number], MessageKey>> = {
  customers: "dataTasks.lists.customers",
  knowledge: "dataTasks.lists.knowledge",
};

/** What the task does, what it fills (`contacts.last_seen_at`) and which cabinet lists wait for it. */
export function DataTaskWhat({ task }: { task: DataTask }) {
  const { t } = useI18n();
  return (
    <>
      <div>
        {task.kind === "migrate_documents"
          ? t("dataTasks.kinds.migrate_documents", { version: String(task.target_version ?? "") })
          : t("dataTasks.kinds.backfill_lookup")}
      </div>
      <div className="font-mono text-xs break-all text-ink-muted" lang="en" dir="ltr">
        {dataTaskTarget(task)}
      </div>
      {task.lists.length > 0 ? (
        <div className="text-xs text-ink-muted">
          {t("dataTasks.holdsBack", { lists: task.lists.map((list) => t(LIST_NAMES[list])).join(", ") })}
        </div>
      ) : null}
    </>
  );
}

export function DataTaskBadges({ task }: { task: DataTask }) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap gap-1">
      <Badge tone={dataTaskTone(task.status)}>{t(STATUS_NAMES[task.status])}</Badge>
      {task.is_stalled ? <Badge tone="danger">{t("dataTasks.isStalled")}</Badge> : null}
    </div>
  );
}

/** How far the walk is against the table's estimated rows, what changed, and what failed. */
export function DataTaskProgress({ task }: { task: DataTask }) {
  const { t } = useI18n();
  const format = useSystemFormat();
  const percent = dataTaskPercent(task);
  return (
    <>
      {percent !== null ? (
        <div
          role="progressbar"
          aria-label={dataTaskTarget(task)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          className="relative mb-1 h-1.5 overflow-hidden rounded-full bg-surface-muted ring-1 ring-line/60"
        >
          <div
            className={
              task.status === "failed"
                ? "absolute inset-y-0 start-0 rounded-full bg-danger"
                : "absolute inset-y-0 start-0 rounded-full bg-accent-solid"
            }
            style={{ width: `${percent}%` }}
          />
        </div>
      ) : null}
      <div>
        {task.row_estimate
          ? t("dataTasks.rows", { scanned: format.number(task.scanned_count), estimate: format.number(task.row_estimate) })
          : t("dataTasks.rowsUnknown", { scanned: format.number(task.scanned_count) })}
      </div>
      <div className="text-ink-muted">
        {t("dataTasks.changed", { count: format.number(task.changed_count), batches: format.number(task.batch_count) })}
      </div>
      {task.failed_row_count > 0 ? (
        <div className="text-danger">
          {t("dataTasks.failedRows", {
            count: format.number(task.failed_row_count),
            keys: task.failed_document_keys.slice(0, 3).join(", "),
          })}
        </div>
      ) : null}
      {task.last_error ? (
        <div className="break-words text-danger" lang="en" dir="ltr">
          {task.last_error}
        </div>
      ) : null}
    </>
  );
}

/** When it was done, or since when it is due and its last batch. */
export function DataTaskWhen({ task }: { task: DataTask }) {
  const { t } = useI18n();
  const format = useSystemFormat();
  if (task.status === "done") {
    return <div>{t("dataTasks.doneAt", { time: format.when(task.finished_at) })}</div>;
  }
  return (
    <>
      <div>{t("dataTasks.dueSince", { time: format.when(task.pending_since) })}</div>
      {task.last_batch_at ? <div>{t("dataTasks.lastBatch", { time: format.when(task.last_batch_at) })}</div> : null}
    </>
  );
}

/** "Walk again" for a failed task (audited); nothing for any other. */
export function DataTaskRetry({ task, isRetrying, onRetry }: { task: DataTask; isRetrying: boolean; onRetry: () => void }) {
  const { t } = useI18n();
  if (task.status !== "failed") {
    return null;
  }
  return (
    <Button
      size="sm"
      variant="secondary"
      className="whitespace-nowrap"
      leadingIcon={<IconRefresh className="size-4" aria-hidden />}
      isLoading={isRetrying}
      loadingText={t("dataTasks.retry")}
      onClick={onRetry}
      aria-label={`${t("dataTasks.retry")}: ${dataTaskTarget(task)}`}
    >
      {t("dataTasks.retry")}
    </Button>
  );
}
