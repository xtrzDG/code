"use client";

import type { ApiError } from "@/api/errors";
import type { ProfileGapsView, ProfileWizardStep, WizardStepView } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconAlert, IconCheck } from "@/components/icons";
import { Alert, Badge, Button, ButtonLink, Drawer, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

/**
 * The "what to add" status under the step list: ready or how many required
 * answers are missing, with a button that opens the full list (GapsDrawer).
 * It stays small so the step form keeps the width.
 */
export function GapsSummary({
  gaps,
  error,
  isLoading,
  onShowList,
  onRetry,
}: {
  gaps: ProfileGapsView | undefined;
  error: ApiError | null;
  isLoading: boolean;
  onShowList: () => void;
  onRetry: () => void;
}) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();

  const items = gaps?.gaps ?? [];
  const blockingCount = items.filter((gap) => gap.is_blocking).length;

  let status;
  if (!gaps) {
    status = error ? (
      <p className="text-sm text-danger">{t("onboarding.gaps.loadFailed")}</p>
    ) : (
      <p className="flex items-center gap-2 text-sm text-ink-muted">
        <Spinner size="sm" />
        {t("onboarding.gaps.checking")}
      </p>
    );
  } else if (gaps.is_ready_for_assembly) {
    status = (
      <p className="flex items-start gap-2 text-sm font-medium text-success">
        <IconCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
        {t("onboarding.gaps.readyTitle")}
      </p>
    );
  } else if (blockingCount > 0) {
    status = (
      <p className="flex items-start gap-2 text-sm font-medium text-warning">
        <IconAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
        {tp("onboarding.gaps.notReady", blockingCount)}
      </p>
    );
  } else if (items.length > 0) {
    status = <p className="text-sm text-ink-muted">{tp("onboarding.gaps.adviceCount", items.length)}</p>;
  } else {
    status = (
      <p className="flex items-start gap-2 text-sm text-ink-muted">
        <IconCheck className="mt-0.5 size-4 shrink-0 text-success" aria-hidden />
        {t("onboarding.gaps.empty")}
      </p>
    );
  }

  return (
    <section
      aria-labelledby="onboarding-gaps-title"
      className="rounded-2xl border border-line bg-surface p-4 shadow-sm"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 id="onboarding-gaps-title" className="text-sm font-semibold text-ink">
          {t("onboarding.gaps.title")}
        </h2>
        {isLoading && gaps ? <Spinner size="sm" className="text-ink-subtle" /> : null}
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-x-4 gap-y-3 lg:flex-col lg:items-stretch">
        <div aria-live="polite" className="min-w-0">
          {status}
        </div>
        <div className="flex flex-wrap gap-2 lg:flex-col">
          {!gaps && error ? (
            <Button size="sm" variant="secondary" onClick={onRetry}>
              {t("common.retry")}
            </Button>
          ) : null}
          {items.length > 0 ? (
            <Button size="sm" variant="secondary" onClick={onShowList} aria-haspopup="dialog">
              {t("onboarding.gaps.showList")}
              <Badge tone={blockingCount > 0 ? "danger" : "neutral"} className="ms-1">
                {items.length}
              </Badge>
            </Button>
          ) : null}
          {gaps?.is_ready_for_assembly ? (
            <ButtonLink href={businessPath(business.id, "assistant")} size="sm">
              {t("onboarding.gaps.toAssistant")}
            </ButtonLink>
          ) : null}
        </div>
      </div>
    </section>
  );
}

/** The full "what to add" list: blocking gaps first, then advice and customer questions. */
export function GapsDrawer({
  open,
  onClose,
  gaps,
  steps,
  onOpenStep,
}: {
  open: boolean;
  onClose: () => void;
  gaps: ProfileGapsView | undefined;
  steps: readonly WizardStepView[];
  onOpenStep: (step: ProfileWizardStep) => void;
}) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const stepTitle = (step: ProfileWizardStep) => steps.find((item) => item.step === step)?.title ?? step;
  const items = [...(gaps?.gaps ?? [])].sort((left, right) => Number(right.is_blocking) - Number(left.is_blocking));

  return (
    <Drawer open={open} onClose={onClose} title={t("onboarding.gaps.title")} description={t("onboarding.gaps.drawerDescription")}>
      <div className="space-y-4">
        {gaps?.is_ready_for_assembly ? (
          <Alert
            tone="success"
            title={t("onboarding.gaps.readyTitle")}
            action={
              <ButtonLink href={businessPath(business.id, "assistant")} size="sm">
                {t("onboarding.gaps.toAssistant")}
              </ButtonLink>
            }
          >
            {t("onboarding.gaps.readyDescription")}
          </Alert>
        ) : null}

        {items.length === 0 ? (
          <p className="flex items-center gap-2 text-sm text-ink-muted">
            <IconCheck className="size-4 text-success" aria-hidden />
            {t("onboarding.gaps.empty")}
          </p>
        ) : (
          <ul className="space-y-3">
            {items.map((gap, index) => (
              <li key={`${gap.kind}-${gap.question_key ?? gap.unanswered_question_id ?? index}`}>
                <button
                  type="button"
                  onClick={() => onOpenStep(gap.step)}
                  className="w-full rounded-xl border border-line p-3 text-start transition-colors hover:border-line-strong hover:bg-surface-muted/60 focus-visible:outline-2 focus-visible:outline-focus"
                >
                  <span className="mb-1.5 flex flex-wrap items-center gap-2">
                    <Badge tone={gap.is_blocking ? "danger" : "neutral"}>
                      {gap.is_blocking ? t("onboarding.gaps.blocking") : t("onboarding.gaps.advice")}
                    </Badge>
                    <span className="text-xs text-ink-subtle">{stepTitle(gap.step)}</span>
                  </span>
                  <span className="block text-sm text-ink">{gap.description}</span>
                  {gap.unanswered_question ? (
                    <span className="mt-1 block text-sm text-ink-muted" dir="auto">
                      {t("onboarding.gaps.customerQuestion", { question: gap.unanswered_question })}
                      {gap.occurrence_count ? ` · ${tp("onboarding.gaps.times", gap.occurrence_count)}` : ""}
                    </span>
                  ) : null}
                  <span className="sr-only">{t("onboarding.gaps.goToStep")}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Drawer>
  );
}
