"use client";

import { useEffect, useState, type ComponentType } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import type { ProfileStepBody, ProfileWizardStep } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { ErrorState, LoadingBlock, PageHeader, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { GapsPanel } from "./_components/GapsPanel";
import { StepNavigation } from "./_components/StepNavigation";
import { BookingStep } from "./_components/steps/BookingStep";
import { ChannelsStep } from "./_components/steps/ChannelsStep";
import { ContactsStep } from "./_components/steps/ContactsStep";
import { FaqStep } from "./_components/steps/FaqStep";
import { NicheStep } from "./_components/steps/NicheStep";
import { OfferStep } from "./_components/steps/OfferStep";
import type { ProfileStepSaveResult, StepProps } from "./_components/types";

const STEP_COMPONENTS: Record<ProfileWizardStep, ComponentType<StepProps>> = {
  niche_and_languages: NicheStep,
  contacts_and_hours: ContactsStep,
  offer: OfferStep,
  booking_rules: BookingStep,
  faq_and_handoff: FaqStep,
  channels: ChannelsStep,
};

/** Steps whose form edits knowledge items (offer, FAQ). */
const KNOWLEDGE_STEPS: ReadonlySet<ProfileWizardStep> = new Set(["offer", "faq_and_handoff"]);

function isWizardStep(value: string | null | undefined): value is ProfileWizardStep {
  return value !== null && value !== undefined && value in STEP_COMPONENTS;
}

/**
 * The six-step profile wizard (concept section 3), driven by
 * GET …/profile/wizard. Each step is saved on its own with
 * PUT …/profile/steps/{step}; "what to add" comes from GET …/profile/gaps.
 */
export function OnboardingWizard({ initialStep }: { initialStep: string | null }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const businessId = business.id;

  const wizard = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/profile/wizard", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    [businessId, locale],
  );
  const gaps = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/profile/gaps", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    [businessId, locale],
  );
  const knowledge = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/knowledge", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    [businessId, locale],
  );

  const [chosenStep, setChosenStep] = useState<ProfileWizardStep | null>(isWizardStep(initialStep) ? initialStep : null);
  const [isDirty, setDirty] = useState(false);

  const saveStep = useApiMutation((step: ProfileWizardStep, body: ProfileStepBody) =>
    api.PUT("/v1/businesses/{business_id}/profile/steps/{step}", {
      params: { path: { business_id: businessId, step } },
      body,
    }),
  );

  useEffect(() => {
    if (!isDirty) {
      return;
    }
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  const steps = [...(wizard.data?.steps ?? [])].sort((left, right) => left.number - right.number);
  const firstIncomplete = steps.find((step) => !step.is_complete)?.step;
  const activeStep: ProfileWizardStep | undefined = chosenStep ?? firstIncomplete ?? steps[0]?.step;
  const activeIndex = steps.findIndex((step) => step.step === activeStep);
  const active = steps[activeIndex];

  const openStep = (step: ProfileWizardStep) => {
    setDirty(false);
    setChosenStep(step);
    window.history.replaceState(window.history.state, "", `?step=${step}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const goTo = (step: ProfileWizardStep) => {
    if (step === activeStep) {
      return;
    }
    if (isDirty && !window.confirm(t("onboarding.leaveUnsaved"))) {
      return;
    }
    openStep(step);
  };

  const onSave = async (body: ProfileStepBody, options: { advance: boolean }): Promise<ProfileStepSaveResult | null> => {
    if (!activeStep) {
      return null;
    }
    const result = await saveStep.run(activeStep, body);
    if (!result.ok) {
      return null;
    }
    setDirty(false);
    // Stay on this step when the reloaded wizard marks it complete.
    setChosenStep(activeStep);
    toast.success(t("onboarding.savedStep"));
    wizard.reload();
    gaps.reload();
    if (KNOWLEDGE_STEPS.has(activeStep)) {
      knowledge.reload();
    }
    const next = steps[activeIndex + 1];
    if (options.advance && next) {
      openStep(next.step);
    }
    return result.data;
  };

  const StepComponent = activeStep ? STEP_COMPONENTS[activeStep] : null;

  return (
    <>
      <PageHeader
        eyebrow={active ? t("onboarding.stepOf", { number: active.number, total: steps.length }) : undefined}
        title={t("onboarding.title")}
        description={t("onboarding.subtitle")}
      />

      {!wizard.data ? (
        wizard.error ? (
          <ErrorState error={wizard.error} onRetry={wizard.reload} />
        ) : (
          <LoadingBlock label={t("common.loading")} />
        )
      ) : (
        <div className="grid gap-6 lg:grid-cols-[16rem_minmax(0,1fr)] xl:grid-cols-[16rem_minmax(0,1fr)_20rem]">
          <div className="lg:sticky lg:top-6 lg:self-start">
            {activeStep ? <StepNavigation steps={steps} activeStep={activeStep} onSelect={goTo} /> : null}
          </div>

          <div className="min-w-0 space-y-4">
            {isDirty ? (
              <p className="text-sm text-warning" role="status">
                {t("onboarding.unsaved")}
              </p>
            ) : null}
            {StepComponent && active && activeStep ? (
              <StepComponent
                key={`${activeStep}-${locale}`}
                wizard={wizard.data}
                step={active}
                knowledge={knowledge.data?.items}
                canEdit={isOwner}
                isSaving={saveStep.isPending}
                isLastStep={activeIndex === steps.length - 1}
                onSave={onSave}
                onChange={() => setDirty(true)}
                onProgressChanged={() => {
                  wizard.reload();
                  gaps.reload();
                }}
              />
            ) : null}
          </div>

          <aside className="lg:col-span-2 xl:col-span-1 xl:sticky xl:top-6 xl:self-start">
            <GapsPanel
              gaps={gaps.data}
              error={gaps.error}
              isLoading={gaps.isLoading}
              steps={steps}
              onOpenStep={goTo}
              onRetry={gaps.reload}
            />
          </aside>
        </div>
      )}
    </>
  );
}
