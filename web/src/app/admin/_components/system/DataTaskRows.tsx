"use client";

import { TBody, THead, Td, Th, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { useMediaQuery } from "@/lib/useMediaQuery";

import { ScrollingTable } from "../metrics/ScrollingTable";
import type { DataTask } from "../../_lib/dataTasks";
import { DataTaskBadges, DataTaskProgress, DataTaskRetry, DataTaskWhat, DataTaskWhen } from "./DataTaskParts";

/** Below Tailwind's sm (40rem) the tasks stack as a list instead of a table that scrolls sideways. */
const PHONE_QUERY = "(max-width: 39.98rem)";

type DataTasksProps = {
  caption: string;
  tasks: readonly DataTask[];
  retryingKey: string | null;
  onRetry: (task: DataTask) => void;
};

/** One group of data tasks (open or done): a table on wide screens, a stacked list on a phone. */
export function DataTasks(props: DataTasksProps) {
  const isPhone = useMediaQuery(PHONE_QUERY);
  return isPhone ? <DataTaskItems {...props} /> : <DataTasksTable {...props} />;
}

function DataTasksTable({ caption, tasks, retryingKey, onRetry }: DataTasksProps) {
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
          <Tr key={task.key}>
            <Td className="min-w-56">
              <DataTaskWhat task={task} />
            </Td>
            <Td>
              <DataTaskBadges task={task} />
            </Td>
            <Td className="min-w-48 text-xs">
              <DataTaskProgress task={task} />
            </Td>
            <Td className="text-xs whitespace-nowrap text-ink-muted">
              <DataTaskWhen task={task} />
            </Td>
            {hasActions ? (
              <Td align="right">
                <DataTaskRetry task={task} isRetrying={retryingKey === task.key} onRetry={() => onRetry(task)} />
              </Td>
            ) : null}
          </Tr>
        ))}
      </TBody>
    </ScrollingTable>
  );
}

function DataTaskItems({ caption, tasks, retryingKey, onRetry }: DataTasksProps) {
  return (
    <ul aria-label={caption} className="divide-y divide-line">
      {tasks.map((task) => (
        <li key={task.key} className="space-y-2 px-5 py-3 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <DataTaskWhat task={task} />
            </div>
            <div className="shrink-0">
              <DataTaskBadges task={task} />
            </div>
          </div>
          <div className="text-xs">
            <DataTaskProgress task={task} />
          </div>
          <div className="text-xs text-ink-muted">
            <DataTaskWhen task={task} />
          </div>
          <DataTaskRetry task={task} isRetrying={retryingKey === task.key} onRetry={() => onRetry(task)} />
        </li>
      ))}
    </ul>
  );
}
