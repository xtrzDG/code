"use client";

import { useState } from "react";

import { IconPlus } from "@/components/icons";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { Badge, Button, Card, ErrorState, LoadingRegion, PageHeader, SkeletonCard } from "@/components/ui";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";

import type { CreateIncidentBody } from "../../_lib/incidentForm";
import { attentionCount } from "../../_lib/system";
import { useAdminSystem } from "../../_lib/useAdminSystem";
import { useIncidents } from "../../_lib/useIncidents";
import { AlertsCard } from "./AlertsCard";
import { AnnouncementsCard } from "./AnnouncementsCard";
import { ChannelsCard } from "./ChannelsCard";
import { DataTasksCard } from "./DataTasksCard";
import { DeadLettersCard } from "./DeadLettersCard";
import { ErrorBudgetCard } from "./ErrorBudgetCard";
import { IncidentDialog } from "./IncidentDialog";
import { IncidentsCard } from "./IncidentsCard";
import { BackupsCard, DatabaseCard } from "./StorageCards";
import { LanesCard, WorkersCard } from "./WorkersAndQueues";

/**
 * /admin/system: what on call looks at first (docs/operations/slo.md). The
 * platform alerts, worker pulses, queue lanes and dead letters, channels in
 * error and expiring tokens, the database's size and the backups, and the
 * incident log with "Record incident". Every figure is an indexed count or
 * the database catalog; the page looks again every 30 seconds. The SLOs'
 * error budgets and the announcements of the public status page sit under
 * the alerts.
 */
export function SystemScreen() {
  const { t, tp } = useI18n();
  const toast = useToast();
  const system = useAdminSystem();
  const { incidents, record, isRecording, createError } = useIncidents();
  const [isRecordOpen, setRecordOpen] = useState(false);
  const data = system.data;
  const attention = data ? attentionCount(data) : null;

  const recordIncident = async (body: CreateIncidentBody) => {
    const incident = await record(body);
    if (incident) {
      toast.success(
        incident.notified_owner_count > 0
          ? tp("adminSystem.incidents.recordedNotified", incident.notified_owner_count)
          : t("adminSystem.incidents.recorded"),
      );
    }
    return incident;
  };

  return (
    <>
      <PageHeader
        title={t("adminSystem.title")}
        description={t("adminSystem.description")}
        actions={
          <div className="flex flex-wrap items-center gap-3">
            {attention !== null ? (
              <Badge tone={attention > 0 ? "warning" : "success"}>
                {attention > 0 ? tp("adminSystem.attention", attention) : t("adminSystem.allClear")}
              </Badge>
            ) : null}
            <LiveStatus updatedAt={system.updatedAt} isFetching={system.isFetching && data !== undefined} />
            <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setRecordOpen(true)}>
              {t("adminSystem.incidents.record")}
            </Button>
          </div>
        }
      />

      {system.error && !data ? (
        <Card>
          <ErrorState error={system.error} onRetry={system.reload} />
        </Card>
      ) : !data ? (
        <SystemSkeleton />
      ) : (
        <div className="space-y-6">
          <AlertsCard alerts={data.alerts} />
          <ErrorBudgetCard />
          <AnnouncementsCard />
          {/* Full width: both tables have six columns. */}
          <WorkersCard workers={data.workers} />
          <LanesCard lanes={data.lanes} />
          <DeadLettersCard tallies={data.dead_jobs} />
          <DataTasksCard />
          <div className="grid gap-6 xl:grid-cols-2">
            <ChannelsCard
              inError={data.channels_in_error}
              inErrorCount={data.channels_in_error_count}
              expiring={data.expiring_credentials}
            />
            <BackupsCard system={data} />
          </div>
          <DatabaseCard totalBytes={data.database_bytes} tables={data.tables} />
          <IncidentsCard incidents={incidents} onRecord={() => setRecordOpen(true)} />
        </div>
      )}

      <IncidentDialog
        open={isRecordOpen}
        onClose={() => setRecordOpen(false)}
        onRecord={recordIncident}
        isRecording={isRecording}
        error={createError}
      />
    </>
  );
}

/** The cards while the page loads (also the route's loading.tsx). */
export function SystemSkeleton() {
  const { t } = useI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <div className="space-y-6">
        <SkeletonCard lines={3} />
        <div className="grid gap-6 xl:grid-cols-2">
          <SkeletonCard lines={4} />
          <SkeletonCard lines={4} />
        </div>
        <SkeletonCard lines={3} />
      </div>
    </LoadingRegion>
  );
}
