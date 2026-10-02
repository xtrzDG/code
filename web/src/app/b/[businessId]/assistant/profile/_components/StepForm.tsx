"use client";

import type { FormEvent, ReactNode } from "react";

import { Alert, Button, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * The card of one wizard step: title, the step's fields and the save
 * buttons. `onSubmit(advance)` is called with true for "Save and continue".
 */
export function StepForm({
  title,
  description,
  canEdit,
  isSaving,
  isLastStep,
  onSubmit,
  children,
}: {
  title: string;
  description?: string;
  canEdit: boolean;
  isSaving: boolean;
  isLastStep: boolean;
  onSubmit: (advance: boolean) => void;
  children: ReactNode;
}) {
  const { t } = useI18n();

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLElement | null;
    onSubmit(submitter?.dataset.advance === "true");
  };

  return (
    <form noValidate onSubmit={handleSubmit}>
      <Card
        title={title}
        description={description}
        footer={
          canEdit ? (
            <>
              {!isLastStep ? (
                <Button type="submit" variant="secondary" data-advance="false" disabled={isSaving}>
                  {t("onboarding.save")}
                </Button>
              ) : null}
              <Button
                type="submit"
                data-advance={isLastStep ? "false" : "true"}
                isLoading={isSaving}
                loadingText={t("common.saving")}
              >
                {isLastStep ? t("onboarding.save") : t("onboarding.saveAndContinue")}
              </Button>
            </>
          ) : undefined
        }
      >
        {!canEdit ? (
          <Alert tone="info" className="mb-6">
            {t("onboarding.ownerOnly")}
          </Alert>
        ) : null}
        <fieldset disabled={!canEdit || isSaving} className="min-w-0 space-y-8">
          {children}
        </fieldset>
      </Card>
    </form>
  );
}

/** A titled group of fields inside a step. */
export function StepSection({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <section className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        {hint ? <p className="text-sm text-ink-muted">{hint}</p> : null}
      </div>
      {children}
    </section>
  );
}
