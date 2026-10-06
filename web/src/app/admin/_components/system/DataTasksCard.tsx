"use client";

import { useId, useState } from "react";

import { IconCheckCircle, IconChevronDown } from "@/components/icons";
import { Badge, Button, Card, EmptyState, ErrorState, SkeletonText } from "@/components/ui";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";

import { splitDataTasks, type DataTask, type DataTasksView } from "../../_lib/dataTasks";
import { useDataTasks } from "../../_lib/useDataTasks";
import { DataTasks } from "./DataTaskRows";
import { useSystemFormat } from "./useSystemFormat";

/**
 * The post-deploy data tasks: how far each walk is, which failed and why,
 * whether the release overlap is over (they start only then), and "walk
 * again" for a failed one (audited). The open tasks are listed, failed
 * ones first; the done ones fold away behind a toggle. The promotion of
 * the next release waits for every task (docs/operations/deploys.md).
 */
export function DataTasksCard() {
  const { t } = useI18n();
  const toast = useToast();
  const format = useSystemFormat();
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
      description={t("dataTasks.description", { size: format.number(view?.batch_size ?? 5000) })}
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
            <DataTaskLists tasks={view.tasks} retryingKey={isRetrying ? retrying : null} onRetry={(task) => void retry(task)} />
          )}
        </>
      )}
    </Card>
  );
}

function DataTaskLists({
  tasks,
  retryingKey,
  onRetry,
}: {
  tasks: readonly DataTask[];
  retryingKey: string | null;
  onRetry: (task: DataTask) => void;
}) {
  const { t, tp } = useI18n();
  const [showsDone, setShowsDone] = useState(false);
  const doneId = useId();
  const { open, done } = splitDataTasks(tasks);
  return (
    <>
      {open.length > 0 ? (
        <DataTasks caption={t("dataTasks.openCaption")} tasks={open} retryingKey={retryingKey} onRetry={onRetry} />
      ) : null}
      {done.length > 0 ? (
        <div className={open.length > 0 ? "border-t border-line" : undefined}>
          <div className="px-5 py-3">
            <Button
              size="sm"
              variant="ghost"
              leadingIcon={
                <IconChevronDown className={showsDone ? "size-4 rotate-180" : "size-4"} aria-hidden />
              }
              aria-expanded={showsDone}
              aria-controls={doneId}
              onClick={() => setShowsDone((shown) => !shown)}
            >
              {showsDone ? t("dataTasks.hideDone") : tp("dataTasks.showDone", done.length)}
            </Button>
          </div>
          <div id={doneId} hidden={!showsDone}>
            {showsDone ? (
              <DataTasks caption={t("dataTasks.doneCaption")} tasks={done} retryingKey={retryingKey} onRetry={onRetry} />
            ) : null}
          </div>
        </div>
      ) : null}
    </>
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
