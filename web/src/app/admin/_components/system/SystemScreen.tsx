"use client";

import { useMemo, useState } from "react";

import { IconPlus } from "@/components/icons";
import { LiveStatus } from "@/components/shell/LiveStatus";
import { Badge, Button, Card, ErrorState, LoadingRegion, PageHeader, PhoneFold, PhoneFolds, SkeletonCard } from "@/components/ui";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";

import type { CreateIncidentBody } from "../../_lib/incidentForm";
import { attentionCount, withCircuits, type AdminSystem } from "../../_lib/system";
import { useAdminSystem } from "../../_lib/useAdminSystem";
import { useIncidents } from "../../_lib/useIncidents";
import { AlertsCard } from "./AlertsCard";
import { AnnouncementsCard } from "./AnnouncementsCard";
import { ChannelsCard } from "./ChannelsCard";
import { CircuitsCard } from "./CircuitsCard";
import { DataTasksCard } from "./DataTasksCard";
import { DeadLettersCard } from "./DeadLettersCard";
import { ErrorBudgetCard } from "./ErrorBudgetCard";
import { IncidentDialog } from "./IncidentDialog";
import { IncidentsCard } from "./IncidentsCard";
import { BackupsCard, DatabaseCard } from "./StorageCards";
import { CampaignHoldsCard } from "./CampaignHoldsCard";
import { PaymentReconciliationCard } from "./PaymentReconciliationCard";
import { PlatformBrakesCard } from "./PlatformBrakesCard";
import { useSystemFolds } from "./systemFolds";
import { LanesCard, WorkersCard } from "./WorkersAndQueues";

/** The folded rows a person opened on a phone, remembered for them (lib/userPreference.ts). */
const OPEN_FOLDS_PREFERENCE = "admin-system-open";

type IncidentLog = ReturnType<typeof useIncidents>["incidents"];

/**
 * /admin/system: what on call looks at first (docs/operations/slo.md). The
 * platform alerts, worker pulses and the providers' circuit breakers, queue
 * lanes and dead letters, channels in error and expiring tokens, the database's size and the backups, and the
 * incident log with "Record incident". Every figure is an indexed count or
 * the database catalog; the page looks again every 30 seconds. The SLOs'
 * error budgets and the announcements of the public status page sit under
 * the alerts. The platform's brakes (the global pause, which `canPause`
 * SUPER admins set, and the daily budget stop) come first, the daily
 * payment reconciliation after the dead letters. The campaigns held over
 * their opt-out rate follow the alerts (SUPER admins release them).
 *
 * On a phone the brakes, the alerts, the held campaigns and the error
 * budgets stay open; every card after them folds into a row with its
 * figure or state (PhoneFold, systemFolds.tsx) that opens on a tap, so the
 * page reads as one status board. Large screens show every card.
 */
export function SystemScreen({ canPause = false, userId }: { canPause?: boolean; userId: string }) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const system = useAdminSystem();
  const { incidents, record, isRecording, createError } = useIncidents();
  const [isRecordOpen, setRecordOpen] = useState(false);
  const data = useMemo(() => (system.data ? withCircuits(system.data) : undefined), [system.data]);
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
    <PhoneFolds preference={OPEN_FOLDS_PREFERENCE} userId={userId}>
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
          <PlatformBrakesCard canPause={canPause} />
          <AlertsCard alerts={data.alerts} />
          <CampaignHoldsCard canRelease={canPause} />
          <ErrorBudgetCard />
          <SystemDetails data={data} incidents={incidents} onRecord={() => setRecordOpen(true)} />
        </div>
      )}

      <IncidentDialog
        open={isRecordOpen}
        onClose={() => setRecordOpen(false)}
        onRecord={recordIncident}
        isRecording={isRecording}
        error={createError}
      />
    </PhoneFolds>
  );
}

/**
 * The cards after the error budgets, each a PhoneFold: one row each on a
 * phone, the cards themselves from large screens (a flex column, as the
 * folds' wrappers take no box there).
 */
function SystemDetails({ data, incidents, onRecord }: { data: AdminSystem; incidents: IncidentLog; onRecord: () => void }) {
  const { t } = useI18n();
  const folds = useSystemFolds(data, incidents.items);
  return (
    <div className="flex flex-col gap-6 max-lg:gap-4">
      <PhoneFold name="announcements" title={t("adminStatus.title")}>
        <AnnouncementsCard />
      </PhoneFold>
      {/* Full width: both tables have six columns. */}
      <PhoneFold name="workers" title={t("adminSystem.workers.title")} summary={folds.workers}>
        <WorkersCard workers={data.workers} />
      </PhoneFold>
      <PhoneFold name="circuits" title={t("providerCircuits.title")} summary={folds.circuits}>
        <CircuitsCard circuits={data.circuits} />
      </PhoneFold>
      <PhoneFold name="lanes" title={t("adminSystem.lanes.title")} summary={folds.lanes}>
        <LanesCard lanes={data.lanes} />
      </PhoneFold>
      <PhoneFold name="dead-letters" title={t("adminSystem.deadLetters.title")} summary={folds.deadLetters}>
        <DeadLettersCard tallies={data.dead_jobs} />
      </PhoneFold>
      <PhoneFold name="reconciliation" title={t("platformBrakes.reconciliation.title")} summary={folds.reconciliation}>
        <PaymentReconciliationCard />
      </PhoneFold>
      <PhoneFold name="data-tasks" title={t("dataTasks.title")}>
        <DataTasksCard />
      </PhoneFold>
      <div className="grid gap-6 max-lg:gap-4 xl:grid-cols-2">
        <PhoneFold name="channels" title={t("adminSystem.channels.title")} summary={folds.channels}>
          <ChannelsCard
            inError={data.channels_in_error}
            inErrorCount={data.channels_in_error_count}
            expiring={data.expiring_credentials}
          />
        </PhoneFold>
        <PhoneFold name="backups" title={t("adminSystem.backups.title")} summary={folds.backups}>
          <BackupsCard system={data} />
        </PhoneFold>
      </div>
      <PhoneFold name="database" title={t("adminSystem.database.title")} summary={folds.database}>
        <DatabaseCard totalBytes={data.database_bytes} tables={data.tables} />
      </PhoneFold>
      <PhoneFold name="incidents" title={t("adminSystem.incidents.title")} summary={folds.incidents}>
        <IncidentsCard incidents={incidents} onRecord={onRecord} />
      </PhoneFold>
    </div>
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
