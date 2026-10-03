"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, type ComponentType } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import type { ProfileStepBody, ProfileWizardStep } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { ErrorState, LoadingRegion, PageHeader, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { GapsDrawer, GapsSummary } from "./_components/GapsPanel";
import { StepNavigation } from "./_components/StepNavigation";
import { WizardSkeleton } from "./_components/WizardSkeleton";
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
  return value !== null && value !== undefined && Object.hasOwn(STEP_COMPONENTS, value);
}

/**
 * Shows the step in the address (`?step=offer`) without a navigation. The
 * null state lets Next.js sync useSearchParams (its own history state would
 * make the router skip the update).
 */
function showStepInUrl(step: ProfileWizardStep): void {
  const query = new URLSearchParams(window.location.search);
  query.set("step", step);
  window.history.replaceState(null, "", `${window.location.pathname}?${query.toString()}`);
}

/**
 * The six-step profile wizard (concept section 3), driven by
 * GET …/profile/wizard. Each step is saved on its own with
 * PUT …/profile/steps/{step}; "what to add" comes from GET …/profile/gaps.
 * The open step is the `step` query parameter, else the first incomplete one.
 */
export function OnboardingWizard() {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business, isOwner } = useBusiness();
  const businessId = business.id;

  // The steps' forms start from these and save them back: never from a cached copy.
  const wizard = useQuery(
    queryKeys.profile.wizard(businessId, locale),
    () =>
      api.GET("/v1/businesses/{business_id}/profile/wizard", {
        params: { path: { business_id: businessId }, query: { language: locale } },
      }),
    { requireFresh: true },
  );
  const gaps = useQuery(queryKeys.profile.gaps(businessId, locale), () =>
    api.GET("/v1/businesses/{business_id}/profile/gaps", {
      params: { path: { business_id: businessId }, query: { language: locale } },
    }),
  );
  const knowledge = useQuery(
    queryKeys.knowledge.wizardItems(businessId, locale),
    () =>
      // The offer and FAQ steps edit the whole list: the largest page the API serves.
      api.GET("/v1/businesses/{business_id}/knowledge", {
        params: { path: { business_id: businessId }, query: { language: locale, limit: "200" } },
      }),
    { requireFresh: true },
  );

  const searchParams = useSearchParams();
  const requestedStep = searchParams.get("step");
  const chosenStep = isWizardStep(requestedStep) ? requestedStep : null;
  // The step whose form has unsaved edits (a link to another step drops them).
  const [dirtyStep, setDirtyStep] = useState<ProfileWizardStep | null>(null);
  const [isGapsListOpen, setGapsListOpen] = useState(false);

  const saveStep = useMutation(
    (step: ProfileWizardStep, body: ProfileStepBody) =>
      api.PUT("/v1/businesses/{business_id}/profile/steps/{step}", {
        params: { path: { business_id: businessId, step } },
        body,
      }),
    {
      // Everything built from the profile follows when shown next.
      stale: [
        queryKeys.business.all(businessId),
        queryKeys.knowledge.all(businessId),
        queryKeys.resources.all(businessId),
        queryKeys.assistant.all(businessId),
        queryKeys.dashboard.all(businessId),
      ],
    },
  );

  const steps = [...(wizard.data?.steps ?? [])].sort((left, right) => left.number - right.number);
  const firstIncomplete = steps.find((step) => !step.is_complete)?.step;
  const activeStep: ProfileWizardStep | undefined = chosenStep ?? firstIncomplete ?? steps[0]?.step;
  const activeIndex = steps.findIndex((step) => step.step === activeStep);
  const active = steps[activeIndex];
  const isDirty = dirtyStep !== null && dirtyStep === activeStep;

  useEffect(() => {
    if (!isDirty) {
      return;
    }
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  const openStep = (step: ProfileWizardStep) => {
    setDirtyStep(null);
    showStepInUrl(step);
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
    setDirtyStep(null);
    // Stay on this step when the reloaded wizard marks it complete.
    if (chosenStep !== activeStep) {
      showStepInUrl(activeStep);
    }
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
          <LoadingRegion label={t("common.loading")}>
            <WizardSkeleton />
          </LoadingRegion>
        )
      ) : (
        <div className="grid gap-6 lg:grid-cols-[15rem_minmax(0,1fr)] lg:gap-8">
          <div className="min-w-0 space-y-4 lg:sticky lg:top-6 lg:self-start">
            {activeStep ? <StepNavigation steps={steps} activeStep={activeStep} onSelect={goTo} /> : null}
            <GapsSummary
              gaps={gaps.data}
              error={gaps.error}
              isLoading={gaps.isLoading}
              onShowList={() => setGapsListOpen(true)}
              onRetry={gaps.reload}
            />
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
                onChange={() => setDirtyStep(activeStep)}
                onProgressChanged={() => {
                  wizard.reload();
                  gaps.reload();
                }}
              />
            ) : null}
          </div>

          <GapsDrawer
            open={isGapsListOpen}
            onClose={() => setGapsListOpen(false)}
            gaps={gaps.data}
            steps={steps}
            onOpenStep={(step) => {
              setGapsListOpen(false);
              goTo(step);
            }}
          />
        </div>
      )}
    </>
  );
}
