"use client";

import { IconAlert } from "@/components/icons";
import { Badge, Card, EmptyState, TBody, THead, Td, Th, Tr } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { ScrollingTable } from "../metrics/ScrollingTable";
import { laneTone, sortWorkers, type Lane, type WorkerPulse } from "../../_lib/system";
import { LANE_NAMES, useSystemFormat } from "./useSystemFormat";

/** Each worker process: where it runs, which release, when it last beat, and the jobs failing on it. */
export function WorkersCard({ workers }: { workers: readonly WorkerPulse[] }) {
  const { t } = useI18n();
  const format = useSystemFormat();
  const title = t("adminSystem.workers.title");
  return (
    <Card aria-label={title} title={title} description={t("adminSystem.workers.description")} padded={workers.length === 0}>
      {workers.length === 0 ? (
        <EmptyState
          icon={<IconAlert className="size-6 text-danger" />}
          title={t("adminSystem.workers.none")}
          description={t("adminSystem.workers.noneDescription")}
        />
      ) : (
        <ScrollingTable caption={title}>
          <THead>
            <Tr>
              <Th>{t("adminSystem.workers.host")}</Th>
              <Th>{t("adminSystem.workers.state")}</Th>
              <Th>{t("adminSystem.workers.lastBeat")}</Th>
              <Th>{t("adminSystem.workers.release")}</Th>
              <Th>{t("adminSystem.workers.started")}</Th>
              <Th>{t("adminSystem.workers.failing")}</Th>
            </Tr>
          </THead>
          <TBody>
            {sortWorkers(workers).map((worker) => (
              <Tr key={worker.worker_id}>
                <Td className="font-mono text-xs break-all">{worker.host_name}</Td>
                <Td>
                  <Badge tone={worker.is_stale ? "danger" : "success"}>
                    {t(worker.is_stale ? "adminSystem.workers.stale" : "adminSystem.workers.live")}
                  </Badge>
                </Td>
                <Td className={cn("whitespace-nowrap", worker.is_stale && "text-danger")}>{format.ago(worker.age_seconds)}</Td>
                <Td className="font-mono text-xs">{worker.release ?? "—"}</Td>
                <Td className="whitespace-nowrap text-ink-muted">{format.when(worker.started_at)}</Td>
                <Td className="font-mono text-xs">{worker.failing_jobs.length > 0 ? worker.failing_jobs.join(", ") : "—"}</Td>
              </Tr>
            ))}
          </TBody>
        </ScrollingTable>
      )}
    </Card>
  );
}

/** Each queue lane: due, scheduled, running and dead jobs, and the oldest due job's wait. */
export function LanesCard({ lanes }: { lanes: readonly Lane[] }) {
  const { t } = useI18n();
  const format = useSystemFormat();
  const title = t("adminSystem.lanes.title");
  return (
    <Card aria-label={title} title={title} description={t("adminSystem.lanes.description")} padded={false}>
      <ScrollingTable caption={title}>
        <THead>
          <Tr>
            <Th>{t("adminSystem.lanes.lane")}</Th>
            <Th align="right">{t("adminSystem.lanes.waiting")}</Th>
            <Th align="right">{t("adminSystem.lanes.scheduled")}</Th>
            <Th align="right">{t("adminSystem.lanes.running")}</Th>
            <Th align="right">{t("adminSystem.lanes.dead")}</Th>
            <Th align="right">{t("adminSystem.lanes.oldest")}</Th>
          </Tr>
        </THead>
        <TBody>
          {lanes.map((lane) => {
            const tone = laneTone(lane);
            return (
              <Tr key={lane.lane}>
                <Th scope="row" className="py-3 font-medium text-ink">
                  {t(LANE_NAMES[lane.lane])}
                </Th>
                <Td align="right">{format.number(lane.waiting)}</Td>
                <Td align="right" className="text-ink-muted">
                  {format.number(lane.scheduled)}
                </Td>
                <Td align="right">{format.number(lane.running)}</Td>
                <Td align="right" className={cn(lane.dead > 0 && "font-semibold text-danger")}>
                  {format.number(lane.dead)}
                </Td>
                <Td
                  align="right"
                  className={cn("whitespace-nowrap", tone === "warning" && "font-semibold text-warning")}
                >
                  {lane.oldest_wait_seconds === null || lane.oldest_wait_seconds === undefined
                    ? "—"
                    : format.duration(lane.oldest_wait_seconds)}
                </Td>
              </Tr>
            );
          })}
        </TBody>
      </ScrollingTable>
    </Card>
  );
}
