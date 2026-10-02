"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCopy, IconFlask, IconRocket, IconUndo } from "@/components/content/icons";
import { Tabs } from "@/components/content/Tabs";
import { IconArrowLeft, IconChat } from "@/components/icons";
import { Alert, Button, ButtonLink, Card, ErrorState, LoadingBlock, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  liveVersion,
  versionActions,
  type AssistantToolName,
  type AssistantVersionDetails,
} from "@/lib/assistant/versions";
import { formatScore, isRunInProgress } from "@/lib/assistant/autotests";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { useAssistant } from "../../_components/AssistantContext";
import { VersionStatusBadge } from "../../_components/VersionStatusBadge";
import { AutotestsPanel } from "./AutotestsPanel";
import { GoLiveChecklist } from "./GoLiveChecklist";
import { PublishDialog, RollbackDialog, RunAutotestsDialog } from "./VersionDialogs";

const POLL_INTERVAL_MS = 3000;

type DetailTab = "autotests" | "facts" | "instruction" | "tools";
type Dialog = "publish" | "forcePublish" | "rollback" | "autotests" | null;

export const TOOL_LABELS: Record<AssistantToolName, { name: MessageKey; description: MessageKey }> = {
  search_knowledge: { name: "assistant.tools.search_knowledge.name", description: "assistant.tools.search_knowledge.description" },
  get_price: { name: "assistant.tools.get_price.name", description: "assistant.tools.get_price.description" },
  check_availability: { name: "assistant.tools.check_availability.name", description: "assistant.tools.check_availability.description" },
  create_booking: { name: "assistant.tools.create_booking.name", description: "assistant.tools.create_booking.description" },
  cancel_booking: { name: "assistant.tools.cancel_booking.name", description: "assistant.tools.cancel_booking.description" },
  reschedule_booking: { name: "assistant.tools.reschedule_booking.name", description: "assistant.tools.reschedule_booking.description" },
  create_lead: { name: "assistant.tools.create_lead.name", description: "assistant.tools.create_lead.description" },
  handoff_to_human: { name: "assistant.tools.handoff_to_human.name", description: "assistant.tools.handoff_to_human.description" },
  send_link: { name: "assistant.tools.send_link.name", description: "assistant.tools.send_link.description" },
  record_unanswered_question: {
    name: "assistant.tools.record_unanswered_question.name",
    description: "assistant.tools.record_unanswered_question.description",
  },
};

/** One assistant version: status, go-live checks, autotests, facts, instruction and tools. */
export function VersionDetailScreen({ versionId }: { versionId: string }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, isOwner, isPlatformAdmin } = useBusiness();
  const format = useBusinessFormat();
  const { versions } = useAssistant();
  const base = businessPath(business.id, "assistant");

  const version = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/assistant-versions/{version_id}", {
        params: { path: { business_id: business.id, version_id: versionId } },
      }),
    [business.id, versionId],
  );
  // A version built without autotests has no run yet (the API answers 404).
  const hasRun = Boolean(version.data?.autotest_run_id) || version.data?.status === "testing";
  const run = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/assistant-versions/{version_id}/autotest-run", {
        params: { path: { business_id: business.id, version_id: versionId } },
      }),
    [business.id, versionId],
    { enabled: hasRun },
  );

  const [tab, setTab] = useState<DetailTab>("autotests");
  const [dialog, setDialog] = useState<Dialog>(null);
  const [checklistKey, setChecklistKey] = useState(0);

  const details = version.data;
  const runData = !hasRun || run.error?.code === "not_found" ? null : (run.data ?? null);
  const isRunning = isRunInProgress(details?.status, runData);

  // While the worker plays the autotests, refresh the version and its run.
  const { reload: reloadVersion } = version;
  const { reload: reloadRun } = run;
  const { reload: reloadVersions } = versions;
  const wasRunning = useRef(false);
  useEffect(() => {
    if (isRunning) {
      wasRunning.current = true;
      const timer = window.setInterval(() => {
        reloadVersion();
        reloadRun();
        setChecklistKey((key) => key + 1);
      }, POLL_INTERVAL_MS);
      return () => window.clearInterval(timer);
    }
    if (wasRunning.current) {
      wasRunning.current = false;
      reloadVersions();
    }
    return undefined;
  }, [isRunning, reloadVersion, reloadRun, reloadVersions]);

  if (version.isLoading && !details) {
    return (
      <Card>
        <LoadingBlock label={t("common.loading")} />
      </Card>
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
    setChecklistKey((key) => key + 1);
  };

  const copyInstruction = async () => {
    try {
      await navigator.clipboard.writeText(details.prompt_text);
      toast.success(t("assistant.detail.copied"));
    } catch {
      toast.show({ tone: "error", title: t("assistant.detail.copyFailed") });
    }
  };

  return (
    <div className="space-y-6">
      <Link href={`${base}/versions`} className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-muted hover:text-ink">
        <IconArrowLeft className="size-4" aria-hidden />
        {t("assistant.detail.back")}
      </Link>

      <Card>
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="text-xl font-semibold text-ink">{t("assistant.versions.number", { number: details.version_number })}</h2>
              <VersionStatusBadge status={details.status} />
            </div>
            <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
              <Meta label={t("assistant.detail.built")}>{format.dateTime(details.created_at)}</Meta>
              {details.published_at ? <Meta label={t("assistant.detail.publishedAt")}>{format.dateTime(details.published_at)}</Meta> : null}
              <Meta label={t("assistant.detail.languages")}>
                {details.languages
                  .map((language) =>
                    language === details.default_language
                      ? t("assistant.detail.mainLanguage", { language: languageName(language, locale) })
                      : languageName(language, locale),
                  )
                  .join(", ")}
              </Meta>
              <Meta label={t("assistant.detail.testScore")}>
                {details.test_score !== null && details.test_score !== undefined
                  ? t("assistant.autotests.scoreValue", { score: formatScore(details.test_score, locale) })
                  : t("assistant.detail.noScore")}
              </Meta>
            </dl>
          </div>
          <div className="flex flex-wrap gap-2 lg:justify-end">
            <ButtonLink
              href={`${base}?version=${encodeURIComponent(details.id)}`}
              variant="secondary"
              leadingIcon={<IconChat className="size-4" aria-hidden />}
            >
              {t("assistant.detail.testInChat")}
            </ButtonLink>
            {canRunAutotests ? (
              <Button
                variant={actions.publish ? "secondary" : "primary"}
                leadingIcon={<IconFlask className="size-4" aria-hidden />}
                onClick={() => setDialog("autotests")}
              >
                {t("assistant.autotests.run")}
              </Button>
            ) : null}
            {actions.publish ? (
              <Button leadingIcon={<IconRocket className="size-4" aria-hidden />} onClick={() => setDialog("publish")}>
                {t("assistant.publish.open")}
              </Button>
            ) : null}
            {actions.forcePublish && !isRunning ? (
              <Button variant="danger" leadingIcon={<IconRocket className="size-4" aria-hidden />} onClick={() => setDialog("forcePublish")}>
                {t("assistant.publish.forceOpen")}
              </Button>
            ) : null}
            {actions.rollback ? (
              <Button variant="danger" leadingIcon={<IconUndo className="size-4" aria-hidden />} onClick={() => setDialog("rollback")}>
                {t("assistant.rollback.open")}
              </Button>
            ) : null}
          </div>
        </div>
        {details.status === "published" ? (
          <Alert tone="success" className="mt-5" title={t("assistant.detail.liveTitle")}>
            {t("assistant.detail.liveDescription")}
          </Alert>
        ) : null}
        {details.status === "archived" ? (
          <Alert tone="info" className="mt-5">
            {t("assistant.detail.archivedDescription")}
          </Alert>
        ) : null}
        {!isOwner && !isPlatformAdmin ? (
          <p className="mt-5 text-sm text-ink-muted">{t("assistant.detail.ownerOnly")}</p>
        ) : null}
      </Card>

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
            { key: "instruction", label: t("assistant.detail.tabs.instruction") },
            { key: "tools", label: t("assistant.detail.tabs.tools") },
          ]}
        >
          {tab === "autotests" ? (
            hasRun && run.isLoading && !run.data && !run.error ? (
              <LoadingBlock label={t("common.loading")} />
            ) : run.error && run.error.code !== "not_found" && !run.data ? (
              <ErrorState error={run.error} onRetry={run.reload} />
            ) : (
              <AutotestsPanel run={runData} isRunning={isRunning} canRun={canRunAutotests} onRun={() => setDialog("autotests")} />
            )
          ) : null}

          {tab === "facts" ? (
            details.facts.length === 0 ? (
              <p className="text-sm text-ink-muted">{t("assistant.detail.noFacts")}</p>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-ink-muted">{t("assistant.detail.factsHint")}</p>
                <dl className="divide-y divide-line rounded-xl border border-line">
                  {details.facts.map((fact) => (
                    <div key={fact.key} className="grid gap-1 px-4 py-3 sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-ink-muted">{fact.label}</dt>
                      <dd className="text-sm break-words whitespace-pre-line text-ink sm:col-span-2" dir="auto">
                        {fact.value}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            )
          ) : null}

          {tab === "instruction" ? (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-ink-muted">{t("assistant.detail.instructionHint")}</p>
                <Button variant="secondary" size="sm" leadingIcon={<IconCopy className="size-4" aria-hidden />} onClick={() => void copyInstruction()}>
                  {t("assistant.detail.copy")}
                </Button>
              </div>
              <pre
                className="max-h-[32rem] overflow-auto rounded-xl border border-line bg-surface-muted p-4 text-xs leading-relaxed break-words whitespace-pre-wrap text-ink"
                dir="auto"
                tabIndex={0}
                aria-label={t("assistant.detail.tabs.instruction")}
              >
                {details.prompt_text}
              </pre>
            </div>
          ) : null}

          {tab === "tools" ? (
            <div className="space-y-6">
              <section className="space-y-3">
                <h3 className="text-sm font-semibold text-ink">{t("assistant.detail.toolsTitle")}</h3>
                <ul className="grid gap-3 sm:grid-cols-2">
                  {details.tools.map((tool) => (
                    <li key={tool} className="rounded-xl border border-line px-4 py-3">
                      <p className="text-sm font-medium text-ink">{t(TOOL_LABELS[tool].name)}</p>
                      <p className="mt-0.5 text-sm text-ink-muted">{t(TOOL_LABELS[tool].description)}</p>
                    </li>
                  ))}
                </ul>
              </section>
              <section className="space-y-3">
                <h3 className="text-sm font-semibold text-ink">{t("assistant.detail.channelsTitle")}</h3>
                <ul className="divide-y divide-line rounded-xl border border-line text-sm">
                  <li className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                    <span className="text-ink">{t("assistant.detail.chatChannels")}</span>
                    <span className="text-ink-muted">{t("assistant.detail.chatChannelsValue")}</span>
                  </li>
                  <li className="flex flex-wrap items-center justify-between gap-2 px-4 py-3">
                    <span className="text-ink">{t("assistant.detail.voice")}</span>
                    <span className="text-ink-muted">
                      {details.is_voice_enabled
                        ? details.voice_agent_id
                          ? t("assistant.detail.voiceReady")
                          : t("assistant.detail.voiceIncluded")
                        : t("assistant.detail.voiceOff")}
                    </span>
                  </li>
                </ul>
                <Link href={businessPath(business.id, "channels")} className="inline-block text-sm font-medium text-accent hover:underline">
                  {t("assistant.detail.openChannels")}
                </Link>
              </section>
            </div>
          ) : null}
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

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-2">
      <dt className="text-ink-subtle">{label}:</dt>
      <dd className="text-ink">{children}</dd>
    </div>
  );
}
