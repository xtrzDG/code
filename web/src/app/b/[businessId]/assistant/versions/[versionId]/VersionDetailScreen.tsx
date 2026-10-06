"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { Tabs } from "@/components/content/Tabs";
import { IconArrowLeft } from "@/components/icons";
import { Card, ErrorState, LoadingRegion, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { onlyOwnerCheckFailures } from "@/lib/assistant/ownerChecks";
import { liveVersion, versionActions, type AssistantVersionDetails } from "@/lib/assistant/versions";
import { businessPath } from "@/lib/navigation";

import { useAssistant } from "../../_components/AssistantContext";
import { VersionHeaderCard, type VersionDialog } from "./_components/VersionHeaderCard";
import { PublishDialog } from "./_components/PublishDialog";
import { RollbackDialog } from "./_components/RollbackDialog";
import { RunAutotestsDialog } from "./_components/RunAutotestsDialog";
import { FactsPanel, InstructionPanel, ToolsPanel } from "./_components/VersionPanels";
import { useVersionDetail } from "./_lib/useVersionDetail";
import { AutotestsPanel } from "./_components/AutotestsPanel";
import { GoLiveChecklist } from "./_components/GoLiveChecklist";
import { VersionDetailSkeleton } from "../../_components/AssistantSkeletons";

type DetailTab = "autotests" | "facts" | "instruction" | "tools";

/**
 * One assistant update: status, go-live checks, checks, facts and tools;
 * platform admins also see the model's instruction.
 */
export function VersionDetailScreen({ versionId, showProblems = false }: { versionId: string; showProblems?: boolean }) {
  const { t } = useI18n();
  const router = useRouter();
  const { business, isOwner, isPlatformAdmin } = useBusiness();
  const { versions } = useAssistant();
  const base = businessPath(business.id, "assistant");
  const { version, run, hasRun, runData, isRunning, checklistKey, refreshChecklist } = useVersionDetail(versionId);

  const [tab, setTab] = useState<DetailTab>("autotests");
  const [dialog, setDialog] = useState<VersionDialog | null>(null);
  const details = version.data;

  if (version.isLoading && !details) {
    return (
      <LoadingRegion label={t("common.loading")}>
        <VersionDetailSkeleton />
      </LoadingRegion>
    );
  }
  if (!details) {
    return (
      <Card>
        <ErrorState error={version.error} onRetry={version.reload} />
      </Card>
    );
  }

  const actions = versionActions(details.status, { isOwner, isPlatformAdmin });
  const live = liveVersion(versions.data ?? []);
  const liveNumber = live && live.id !== details.id ? live.version_number : null;
  const canRunAutotests = actions.runAutotests && !isRunning;
  const ownerFailures =
    runData && !isRunning && runData.status === "finished" && !runData.is_passed ? onlyOwnerCheckFailures(runData.results) : [];

  const afterGoLive = (updated: AssistantVersionDetails) => {
    version.setData(updated);
    setDialog(null);
    versions.reload();
    // The business goes live and its published version changes.
    router.refresh();
  };

  const refreshState = () => {
    version.reload();
    versions.reload();
    refreshChecklist();
  };

  return (
    <div className="space-y-6">
      <Link href={`${base}/versions`} className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink">
        <IconArrowLeft className="size-4 rtl:-scale-x-100" aria-hidden />
        {t("assistant.detail.back")}
      </Link>

      <VersionHeaderCard
        details={details}
        actions={actions}
        canRunAutotests={canRunAutotests}
        isRunning={isRunning}
        ownerFailures={ownerFailures}
        onOpen={setDialog}
      />

      {(isOwner || isPlatformAdmin) && details.status !== "published" && details.status !== "archived" ? (
        <GoLiveChecklist
          versionId={details.id}
          refreshKey={`${details.status}:${checklistKey}`}
          canRunAutotests={canRunAutotests}
          onRunAutotests={() => setDialog("autotests")}
        />
      ) : null}

      <Card>
        <Tabs<DetailTab>
          label={t("assistant.detail.tabsLabel")}
          selected={tab}
          onSelect={setTab}
          tabs={[
            { key: "autotests", label: t("assistant.detail.tabs.autotests") },
            { key: "facts", label: t("assistant.detail.tabs.facts") },
            // The model's instruction is a platform matter (docs/glossary.md).
            ...(isPlatformAdmin ? [{ key: "instruction" as const, label: t("assistant.detail.tabs.instruction") }] : []),
            { key: "tools", label: t("assistant.detail.tabs.tools") },
          ]}
        >
          {tab === "autotests" ? (
            hasRun && run.isLoading && !run.data && !run.error ? (
              <LoadingRegion label={t("common.loading")}>
                <SkeletonText lines={4} />
              </LoadingRegion>
            ) : run.error && run.error.code !== "not_found" && !run.data ? (
              <ErrorState error={run.error} onRetry={run.reload} />
            ) : (
              <AutotestsPanel
                run={runData}
                isRunning={isRunning}
                canRun={canRunAutotests}
                onRun={() => setDialog("autotests")}
                initialOutcome={showProblems ? "problems" : "all"}
              />
            )
          ) : null}

          {tab === "facts" ? <FactsPanel details={details} /> : null}
          {tab === "instruction" && isPlatformAdmin ? <InstructionPanel details={details} /> : null}
          {tab === "tools" ? <ToolsPanel details={details} /> : null}
        </Tabs>
      </Card>

      {dialog === "autotests" ? (
        <RunAutotestsDialog
          version={details}
          onClose={() => setDialog(null)}
          onStarted={(started) => {
            setDialog(null);
            run.setData(started);
            version.reload();
            versions.reload();
            setTab("autotests");
          }}
        />
      ) : null}
      {dialog === "publish" || dialog === "forcePublish" ? (
        <PublishDialog
          version={details}
          liveNumber={liveNumber}
          force={dialog === "forcePublish"}
          onClose={() => setDialog(null)}
          onPublished={afterGoLive}
          onRunAutotests={() => setDialog("autotests")}
          onRefused={refreshState}
        />
      ) : null}
      {dialog === "rollback" ? (
        <RollbackDialog
          version={details}
          liveNumber={liveNumber}
          onClose={() => setDialog(null)}
          onRolledBack={afterGoLive}
          onRefused={refreshState}
        />
      ) : null}
    </div>
  );
}
