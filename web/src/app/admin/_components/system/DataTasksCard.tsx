"use client";

import { useState } from "react";

import { IconCheckCircle, IconRefresh } from "@/components/icons";
import { Badge, Button, Card, EmptyState, ErrorState, SkeletonText, TBody, THead, Td, Th, Tr } from "@/components/ui";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { ScrollingTable } from "../metrics/ScrollingTable";
import {
  dataTaskPercent,
  dataTaskTarget,
  dataTaskTone,
  type DataTask,
  type DataTaskStatus,
  type DataTasksView,
} from "../../_lib/dataTasks";
import { useDataTasks } from "../../_lib/useDataTasks";
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

/**
 * The post-deploy data tasks: how far each walk is, which failed and why,
 * whether the release overlap is over (they start only then), and "walk
 * again" for a failed one (audited). The promotion of the next release
 * waits for every task (docs/operations/deploys.md).
 */
export function DataTasksCard() {
  const { t } = useI18n();
  const toast = useToast();
  const { tasks, walkAgain, isRetrying } = useDataTasks();
  const [retrying, setRetrying] = useState<string | null>(null);
  const view = tasks.data;
  const title = t("dataTasks.title");

  const retry = async (task: DataTask) => {
    setRetrying(task.key);
    if (await walkAgain(task)) {
      toast.success(t("dataTasks.retried"));
    }
    setRetrying(null);
  };

  return (
    <Card
      aria-label={title}
      title={title}
      description={t("dataTasks.description", { size: view ? String(view.batch_size) : "5000" })}
      padded={false}
    >
      {tasks.error && !view ? (
        <div className="p-5">
          <ErrorState error={tasks.error} onRetry={tasks.reload} />
        </div>
      ) : !view ? (
        <div className="p-5">
          <SkeletonText lines={3} />
        </div>
      ) : (
        <>
          <DataTasksSummary view={view} />
          {view.tasks.length === 0 ? (
            <div className="p-5">
              <EmptyState icon={<IconCheckCircle className="size-6 text-success" />} title={t("dataTasks.none")} />
            </div>
          ) : (
            <ScrollingTable caption={title}>
              <THead>
                <Tr>
                  <Th>{t("dataTasks.columns.task")}</Th>
                  <Th>{t("dataTasks.columns.status")}</Th>
                  <Th>{t("dataTasks.columns.progress")}</Th>
                  <Th>{t("dataTasks.columns.when")}</Th>
                  <Th align="right">{t("dataTasks.columns.actions")}</Th>
                </Tr>
              </THead>
              <TBody>
                {view.tasks.map((task) => (
                  <DataTaskRow
                    key={task.key}
                    task={task}
                    isRetrying={isRetrying && retrying === task.key}
                    onRetry={() => void retry(task)}
                  />
                ))}
              </TBody>
            </ScrollingTable>
          )}
        </>
      )}
    </Card>
  );
}

function DataTasksSummary({ view }: { view: DataTasksView }) {
  const { t, tp } = useI18n();
  const format = useSystemFormat();
  const { rollout } = view;
  const waitingFor = (rollout.other_releases ?? []).join(", ");
  return (
    <div className="space-y-2 border-b border-line px-5 py-3 text-sm">
      <ul className="flex flex-wrap gap-2">
        <li>
          <Badge tone={view.open_count > 0 ? "warning" : "success"}>
            {view.open_count > 0 ? tp("dataTasks.open", view.open_count) : t("dataTasks.allDone")}
          </Badge>
        </li>
        {view.failed_count > 0 ? (
          <li>
            <Badge tone="danger">{t("dataTasks.failed", { count: format.number(view.failed_count) })}</Badge>
          </li>
        ) : null}
        {view.stalled_count > 0 ? (
          <li>
            <Badge tone="danger">{t("dataTasks.stalled", { count: format.number(view.stalled_count) })}</Badge>
          </li>
        ) : null}
      </ul>
      <p className="text-ink-muted">
        {rollout.is_settled
          ? t("dataTasks.settled")
          : waitingFor
            ? t("dataTasks.waiting", { releases: waitingFor, time: format.when(rollout.settles_at) })
            : t("dataTasks.waitingUnnamed", { time: format.when(rollout.settles_at) })}
      </p>
    </div>
  );
}

function DataTaskRow({ task, isRetrying, onRetry }: { task: DataTask; isRetrying: boolean; onRetry: () => void }) {
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
        <div className="font-mono text-xs break-all text-ink-muted">{target}</div>
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
              className={task.status === "failed" ? "absolute inset-y-0 start-0 rounded-full bg-danger" : "absolute inset-y-0 start-0 rounded-full bg-accent-solid"}
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
          <div>{t("dataTasks.dueSince", { time: format.when(task.pending_since) })}</div>
        )}
        {task.last_batch_at ? <div>{t("dataTasks.lastBatch", { time: format.when(task.last_batch_at) })}</div> : null}
      </Td>
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
    </Tr>
  );
}
