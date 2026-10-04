"use client";

import Link from "next/link";
import { useState } from "react";

import { IconCheckCircle, IconRefresh, IconTrash } from "@/components/icons";
import { LoadMore } from "@/components/insights/common";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, SkeletonText, TBody, THead, Td, Th, Tr } from "@/components/ui";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";
import type { Schema } from "@/api/types";

import { ScrollingTable } from "../metrics/ScrollingTable";
import { adminClientPath } from "../../_lib/clients";
import type { QueuedJob } from "../../_lib/system";
import { useDeadJobs } from "../../_lib/useDeadJobs";
import { LANE_NAMES, useSystemFormat } from "./useSystemFormat";

/**
 * The queue's dead letters: how many each job has, and each one with its
 * last error, to run again once the cause is fixed or to discard (both
 * audited, on the existing jobs API).
 */
export function DeadLettersCard({ tallies }: { tallies: readonly Schema<"DeadJobTally">[] }) {
  const { t } = useI18n();
  const toast = useToast();
  const { jobs, runAgain, drop, isRetrying, isDiscarding, discardError } = useDeadJobs();
  const [retrying, setRetrying] = useState<string | null>(null);
  const [discarding, setDiscarding] = useState<QueuedJob | null>(null);
  const title = t("adminSystem.deadLetters.title");
  const items = jobs.items;

  const retry = async (job: QueuedJob) => {
    setRetrying(job.id);
    if (await runAgain(job)) {
      toast.success(t("adminSystem.deadLetters.retried"));
    }
    setRetrying(null);
  };

  const confirmDiscard = async () => {
    if (discarding && (await drop(discarding))) {
      setDiscarding(null);
      toast.success(t("adminSystem.deadLetters.discarded"));
    }
  };

  return (
    <Card aria-label={title} title={title} description={t("adminSystem.deadLetters.description")} padded={false}>
      {tallies.length > 0 ? (
        <ul className="flex flex-wrap gap-2 border-b border-line px-5 py-3">
          {tallies.map((tally) => (
            <li key={tally.name}>
              <Badge tone="danger">
                <span className="font-mono">{t("adminSystem.deadLetters.tally", { name: tally.name, count: tally.count })}</span>
              </Badge>
            </li>
          ))}
        </ul>
      ) : null}
      {jobs.error && !items ? (
        <div className="p-5">
          <ErrorState error={jobs.error} onRetry={jobs.reload} />
        </div>
      ) : !items ? (
        <div className="p-5">
          <SkeletonText lines={3} />
        </div>
      ) : items.length === 0 ? (
        <div className="p-5">
          <EmptyState
            icon={<IconCheckCircle className="size-6 text-success" />}
            title={t("adminSystem.deadLetters.none")}
            description={t("adminSystem.deadLetters.noneDescription")}
          />
        </div>
      ) : (
        <>
          <ScrollingTable caption={title}>
            <THead>
              <Tr>
                <Th>{t("adminSystem.deadLetters.job")}</Th>
                <Th>{t("adminSystem.deadLetters.business")}</Th>
                <Th align="right">{t("adminSystem.deadLetters.attempts")}</Th>
                <Th>{t("adminSystem.deadLetters.lastError")}</Th>
                <Th>{t("adminSystem.deadLetters.died")}</Th>
                <Th align="right">{t("adminSystem.deadLetters.actions")}</Th>
              </Tr>
            </THead>
            <TBody>
              {items.map((job) => (
                <DeadJobRow
                  key={job.id}
                  job={job}
                  isRetrying={isRetrying && retrying === job.id}
                  onRetry={() => void retry(job)}
                  onDiscard={() => setDiscarding(job)}
                />
              ))}
            </TBody>
          </ScrollingTable>
          <LoadMore hasMore={jobs.hasMore} isLoading={jobs.isLoadingMore} error={jobs.moreError} onMore={jobs.loadMore} />
        </>
      )}

      <ConfirmDialog
        open={discarding !== null}
        onClose={() => setDiscarding(null)}
        onConfirm={confirmDiscard}
        tone="danger"
        title={t("adminSystem.deadLetters.confirmTitle")}
        description={t("adminSystem.deadLetters.confirmBody", { name: discarding?.name ?? "" })}
        confirmLabel={t("adminSystem.deadLetters.confirm")}
        pendingLabel={t("adminSystem.deadLetters.discarding")}
        isPending={isDiscarding}
        error={discardError}
        errorOverrides={{ conflict: "adminSystem.deadLetters.changed" }}
      />
    </Card>
  );
}

function DeadJobRow({
  job,
  isRetrying,
  onRetry,
  onDiscard,
}: {
  job: QueuedJob;
  isRetrying: boolean;
  onRetry: () => void;
  onDiscard: () => void;
}) {
  const { t } = useI18n();
  const format = useSystemFormat();
  return (
    <Tr>
      <Td>
        <div className="font-mono text-xs break-all">{job.name}</div>
        <div className="text-xs text-ink-muted">{t(LANE_NAMES[job.lane])}</div>
      </Td>
      <Td className="text-xs">
        {job.business_id ? (
          <Link href={adminClientPath(job.business_id)} className="font-mono break-all text-accent-ink underline-offset-2 hover:underline">
            {job.business_id}
          </Link>
        ) : (
          <span className="text-ink-muted">{t("adminSystem.deadLetters.platform")}</span>
        )}
      </Td>
      <Td align="right">{format.number(job.attempts)}</Td>
      <Td className="max-w-80 min-w-48 text-xs break-words text-ink-muted" lang="en" dir="ltr">
        {job.last_error ?? "—"}
      </Td>
      <Td className="whitespace-nowrap text-ink-muted">{format.when(job.updated_at)}</Td>
      <Td align="right">
        <div className="flex justify-end gap-2">
          <Button
            size="sm"
            variant="secondary"
            leadingIcon={<IconRefresh className="size-4" aria-hidden />}
            isLoading={isRetrying}
            loadingText={t("adminSystem.deadLetters.retry")}
            onClick={onRetry}
            aria-label={`${t("adminSystem.deadLetters.retry")}: ${job.name}`}
          >
            {t("adminSystem.deadLetters.retry")}
          </Button>
          <Button
            size="sm"
            variant="danger-ghost"
            leadingIcon={<IconTrash className="size-4" aria-hidden />}
            onClick={onDiscard}
            aria-label={`${t("adminSystem.deadLetters.discard")}: ${job.name}`}
          >
            {t("adminSystem.deadLetters.discard")}
          </Button>
        </div>
      </Td>
    </Tr>
  );
}
