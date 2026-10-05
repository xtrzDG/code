"use client";

/**
 * "Apply changes": what customers do not get yet, one button, and then
 * the same three stages as the tunnel's launch (learning the changes,
 * test conversations, giving customers the new answers). A stop lists
 * its reasons in plain words with the page that fixes each, and the
 * conversation that failed; the owner can close the sheet at any time,
 * the changes reach customers on their own. The owner's checks the live
 * version was not checked against count as changes, and drafts built by
 * hand are listed apart (with "Discard"), so the sheet says everything
 * reaches customers only when nothing of either kind is left.
 */

import { useId } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheck, IconSparkles } from "@/components/icons";
import { LaunchProgress } from "@/components/setup/launch/LaunchProgress";
import { Button, ButtonLink, SkeletonText, Sheet } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { hasPendingWork } from "@/lib/assistant/ownerChecks";
import { summarizeChanges } from "@/lib/assistant/pendingChanges";
import { setupPath } from "@/lib/navigation";

import { ApplyAttention } from "./ApplyAttention";
import { useApplyChanges } from "./ApplyChangesContext";
import { PendingChangesList } from "./PendingChangesList";
import { PendingDrafts } from "./PendingDrafts";
import { PendingOwnerChecks } from "./PendingOwnerChecks";

function SheetBody({ onClose }: { onClose: () => void }) {
  const translator = useI18n();
  const { t } = translator;
  const { business } = useBusiness();
  const { pending, apply, applied } = useApplyChanges();
  const listId = useId();
  const checksId = useId();
  const draftsId = useId();
  const data = pending.data;
  const view = apply.view;

  if (apply.phase === "running" && view) {
    return (
      <div className="space-y-5" aria-live="polite">
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-ink">{t("applyChanges.sheet.runningTitle")}</h3>
          <p className="text-sm text-ink-muted">{t("applyChanges.sheet.running")}</p>
        </div>
        <LaunchProgress
          view={view}
          label={t("applyChanges.sheet.stagesLabel")}
          stageLabel={(stage) => t(`applyChanges.sheet.stages.${stage}`)}
        />
      </div>
    );
  }

  if (apply.phase === "live" && applied !== null && !hasPendingWork(data)) {
    return (
      <div className="space-y-2 rounded-2xl border border-success/30 bg-success-soft/50 p-4" aria-live="polite">
        <p className="flex items-center gap-2 font-semibold text-ink">
          <IconCheck className="size-5 shrink-0 text-success" aria-hidden />
          {t("applyChanges.done.title")}
        </p>
        <p className="text-sm text-ink-muted">{summarizeChanges(applied, translator)}</p>
      </div>
    );
  }

  if (!data) {
    return pending.error ? (
      <div className="space-y-3">
        <p className="text-sm text-danger">{t("applyChanges.sheet.loadFailed")}</p>
        <Button variant="secondary" size="sm" onClick={pending.reload}>
          {t("common.retry")}
        </Button>
      </div>
    ) : (
      <SkeletonText lines={4} />
    );
  }

  if (!data.is_live) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-ink-muted">{t("applyChanges.sheet.notLive")}</p>
        <ButtonLink href={setupPath(business.id)} size="sm" variant="secondary" onClick={onClose}>
          {t("applyChanges.sheet.finishSetup")}
        </ButtonLink>
      </div>
    );
  }

  if (!hasPendingWork(data)) {
    return (
      <p className="flex items-start gap-2 text-sm text-ink-muted">
        <IconCheck className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
        {t("applyChanges.sheet.nothing")}
      </p>
    );
  }

  const isAttention = apply.phase === "attention";
  const changes = data.changes ?? [];
  const checks = data.owner_checks ?? [];
  const drafts = data.drafts ?? [];
  return (
    <div className="space-y-5">
      {isAttention && view ? <ApplyAttention businessId={business.id} view={view} onNavigate={onClose} /> : null}
      {/* After a stop the attention block already says customers keep the previous answers. */}
      {isAttention && data.count > 0 ? null : (
        <p className="text-sm text-ink-muted">{t(data.count > 0 ? "applyChanges.sheet.intro" : "updates.pending.onlyDrafts")}</p>
      )}
      {changes.length > 0 ? (
        <div className="space-y-2">
          <h3 id={listId} className="text-sm font-semibold text-ink">
            {t("applyChanges.sheet.listLabel")}
          </h3>
          <PendingChangesList changes={changes} labelId={listId} />
        </div>
      ) : null}
      {checks.length > 0 ? (
        <section className="space-y-1.5">
          <h3 id={checksId} className="text-sm font-semibold text-ink">
            {t("updates.pending.checksTitle")}
          </h3>
          <p className="text-xs text-ink-subtle">{t("updates.pending.checksHint")}</p>
          <PendingOwnerChecks checks={checks} labelId={checksId} />
        </section>
      ) : null}
      {drafts.length > 0 ? (
        <section className="space-y-1.5">
          <h3 id={draftsId} className="text-sm font-semibold text-ink">
            {t("updates.pending.draftsTitle")}
          </h3>
          <p className="text-xs text-ink-subtle">{t("updates.pending.draftsHint")}</p>
          <PendingDrafts drafts={drafts} labelId={draftsId} onNavigate={onClose} />
        </section>
      ) : null}
    </div>
  );
}

export function ApplyChangesSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useI18n();
  const { pending, apply, start } = useApplyChanges();
  const count = pending.data?.is_live ? pending.data.count : 0;
  const canStart = apply.phase !== "running" && count > 0;

  return (
    <Sheet
      open={open}
      onClose={onClose}
      title={t("applyChanges.sheet.title")}
      footer={
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            {t("applyChanges.sheet.close")}
          </Button>
          {canStart ? (
            <Button
              leadingIcon={<IconSparkles className="size-4" aria-hidden />}
              isLoading={apply.isStarting}
              loadingText={t("applyChanges.sheet.applying")}
              onClick={() => void start()}
            >
              {apply.phase === "attention" ? t("applyChanges.sheet.tryAgain") : t("applyChanges.sheet.apply")}
            </Button>
          ) : null}
        </div>
      }
    >
      <SheetBody onClose={onClose} />
    </Sheet>
  );
}
