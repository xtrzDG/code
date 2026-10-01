"use client";

import type { ProfileGapsView, ProfileWizardStep, WizardStepView } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheck } from "@/components/icons";
import { Alert, Badge, ButtonLink, Card, ErrorState, Spinner } from "@/components/ui";
import type { ApiError } from "@/api/errors";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

/** The "what to add" list: blocking gaps first, then advice and customer questions. */
export function GapsPanel({
  gaps,
  error,
  isLoading,
  steps,
  onOpenStep,
  onRetry,
}: {
  gaps: ProfileGapsView | undefined;
  error: ApiError | null;
  isLoading: boolean;
  steps: readonly WizardStepView[];
  onOpenStep: (step: ProfileWizardStep) => void;
  onRetry: () => void;
}) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const stepTitle = (step: ProfileWizardStep) => steps.find((item) => item.step === step)?.title ?? step;

  const items = gaps?.gaps ?? [];
  const blockingCount = items.filter((gap) => gap.is_blocking).length;

  return (
    <Card
      title={t("onboarding.gaps.title")}
      actions={isLoading && gaps ? <Spinner size="sm" className="text-ink-subtle" /> : undefined}
      aria-live="polite"
    >
      {!gaps ? (
        error ? (
          <ErrorState error={error} onRetry={onRetry} className="py-4" />
        ) : (
          <div className="flex justify-center py-4 text-ink-subtle">
            <Spinner label={t("common.loading")} />
          </div>
        )
      ) : (
        <div className="space-y-4">
          {gaps.is_ready_for_assembly ? (
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
          ) : blockingCount > 0 ? (
            <p className="text-sm font-medium text-warning">{tp("onboarding.gaps.notReady", blockingCount)}</p>
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
                    className="w-full rounded-xl border border-line p-3 text-left transition-colors hover:border-line-strong hover:bg-surface-muted/60"
                  >
                    <div className="mb-1.5 flex flex-wrap items-center gap-2">
                      <Badge tone={gap.is_blocking ? "danger" : "neutral"}>
                        {gap.is_blocking ? t("onboarding.gaps.blocking") : t("onboarding.gaps.advice")}
                      </Badge>
                      <span className="text-xs text-ink-subtle">{stepTitle(gap.step)}</span>
                    </div>
                    <p className="text-sm text-ink">{gap.description}</p>
                    {gap.unanswered_question ? (
                      <p className="mt-1 text-sm text-ink-muted">
                        {t("onboarding.gaps.customerQuestion", { question: gap.unanswered_question })}
                        {gap.occurrence_count ? ` · ${tp("onboarding.gaps.times", gap.occurrence_count)}` : ""}
                      </p>
                    ) : null}
                    <span className="sr-only">{t("onboarding.gaps.goToStep")}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}
