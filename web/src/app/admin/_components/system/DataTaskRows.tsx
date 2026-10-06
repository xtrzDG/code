"use client";

import { IconRefresh } from "@/components/icons";
import { Badge, Button, TBody, THead, Td, Th, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { ScrollingTable } from "../metrics/ScrollingTable";
import { dataTaskPercent, dataTaskTarget, dataTaskTone, type DataTask, type DataTaskStatus } from "../../_lib/dataTasks";
import { useSystemFormat } from "./useSystemFormat";

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

/** One table of data tasks: what each fills, its status, progress and when; "walk again" on a failed one. */
export function DataTasksTable({
  caption,
  tasks,
  retryingKey,
  onRetry,
}: {
  caption: string;
  tasks: readonly DataTask[];
  retryingKey: string | null;
  onRetry: (task: DataTask) => void;
}) {
  const { t } = useI18n();
  // Only a failed task has an action ("walk again"): no empty column otherwise.
  const hasActions = tasks.some((task) => task.status === "failed");
  return (
    <ScrollingTable caption={caption}>
      <THead>
        <Tr>
          <Th>{t("dataTasks.columns.task")}</Th>
          <Th>{t("dataTasks.columns.status")}</Th>
          <Th>{t("dataTasks.columns.progress")}</Th>
          <Th>{t("dataTasks.columns.when")}</Th>
          {hasActions ? <Th align="right">{t("dataTasks.columns.actions")}</Th> : null}
        </Tr>
      </THead>
      <TBody>
        {tasks.map((task) => (
          <DataTaskRow
            key={task.key}
            task={task}
            hasActions={hasActions}
            isRetrying={retryingKey === task.key}
            onRetry={() => onRetry(task)}
          />
        ))}
      </TBody>
    </ScrollingTable>
  );
}

function DataTaskRow({
  task,
  hasActions,
  isRetrying,
  onRetry,
}: {
  task: DataTask;
  hasActions: boolean;
  isRetrying: boolean;
  onRetry: () => void;
}) {
  const { t } = useI18n();
  const format = useSystemFormat();
  const percent = dataTaskPercent(task);
  const target = dataTaskTarget(task);
  const kind =
    task.kind === "migrate_documents"
      ? t("dataTasks.kinds.migrate_documents", { version: String(task.target_version ?? "") })
      : t("dataTasks.kinds.backfill_lookup");
  return (
    <Tr>
      <Td className="min-w-56">
        <div>{kind}</div>
        <div className="font-mono text-xs break-all text-ink-muted" lang="en" dir="ltr">
          {target}
        </div>
        {task.lists.length > 0 ? (
          <div className="text-xs text-ink-muted">
            {t("dataTasks.holdsBack", { lists: task.lists.map((list) => t(LIST_NAMES[list])).join(", ") })}
          </div>
        ) : null}
      </Td>
      <Td>
        <div className="flex flex-wrap gap-1">
          <Badge tone={dataTaskTone(task.status)}>{t(STATUS_NAMES[task.status])}</Badge>
          {task.is_stalled ? <Badge tone="danger">{t("dataTasks.isStalled")}</Badge> : null}
        </div>
      </Td>
      <Td className="min-w-48 text-xs">
        {percent !== null ? (
          <div
            role="progressbar"
            aria-label={target}
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
      </Td>
      <Td className="text-xs whitespace-nowrap text-ink-muted">
        {task.status === "done" ? (
          <div>{t("dataTasks.doneAt", { time: format.when(task.finished_at) })}</div>
        ) : (
          <>
            <div>{t("dataTasks.dueSince", { time: format.when(task.pending_since) })}</div>
            {task.last_batch_at ? <div>{t("dataTasks.lastBatch", { time: format.when(task.last_batch_at) })}</div> : null}
          </>
        )}
      </Td>
      {hasActions ? <RetryCell task={task} target={target} isRetrying={isRetrying} onRetry={onRetry} /> : null}
    </Tr>
  );
}

function RetryCell({
  task,
  target,
  isRetrying,
  onRetry,
}: {
  task: DataTask;
  target: string;
  isRetrying: boolean;
  onRetry: () => void;
}) {
  const { t } = useI18n();
  return (
    <Td align="right">
      {task.status === "failed" ? (
        <Button
          size="sm"
          variant="secondary"
          leadingIcon={<IconRefresh className="size-4" aria-hidden />}
          isLoading={isRetrying}
          loadingText={t("dataTasks.retry")}
          onClick={onRetry}
          aria-label={`${t("dataTasks.retry")}: ${target}`}
        >
          {t("dataTasks.retry")}
        </Button>
      ) : null}
    </Td>
  );
}
