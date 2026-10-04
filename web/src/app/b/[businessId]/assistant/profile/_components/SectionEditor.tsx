"use client";

/**
 * One section of Assistant → Business profile: the matching screen of
 * "Create an AI assistant" in its edit mode (no step counter, no
 * Continue), saving every change by itself. Every save marks what the
 * assistant knows as changed, so the banner over the page counts what
 * customers do not get yet. Only owners change the profile.
 */

import { useRouter } from "next/navigation";
import { useCallback, useMemo, type ReactNode } from "react";

import { invalidate } from "@/api/queryCache";
import { queryKeys } from "@/api/queryKeys";
import { useBusiness } from "@/components/business/BusinessContext";
import { BusinessScreen } from "@/components/setup/flow/BusinessScreen";
import { PlaceScreen } from "@/components/setup/flow/PlaceScreen";
import type { StepContext } from "@/components/setup/flow/stepContext";
import { useSetupData } from "@/components/setup/flow/useSetupData";
import { HoursScreen } from "@/components/setup/hours/HoursScreen";
import { OfferScreen } from "@/components/setup/offer/OfferScreen";
import { PeopleScreen } from "@/components/setup/people/PeopleScreen";
import { RulesScreen } from "@/components/setup/rules/RulesScreen";
import { SaveTrackerProvider } from "@/components/setup/SaveTracker";
import { Alert, ErrorState, LoadingRegion } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { profilePath, type ProfileSection } from "@/lib/profile/sections";

import { EditorBar } from "./EditorBar";
import { SectionEditorSkeleton } from "./ProfileSkeleton";

const SCREENS: Record<ProfileSection, (props: { ctx: StepContext }) => ReactNode> = {
  business: ({ ctx }) => <BusinessScreen ctx={ctx} mode="edit" />,
  place: ({ ctx }) => <PlaceScreen ctx={ctx} mode="edit" />,
  offer: ({ ctx }) => <OfferScreen ctx={ctx} mode="edit" />,
  hours: ({ ctx }) => <HoursScreen ctx={ctx} mode="edit" />,
  people: ({ ctx }) => <PeopleScreen ctx={ctx} mode="edit" />,
  rules: ({ ctx }) => <RulesScreen ctx={ctx} />,
};

/** What the assistant knows changed: the "not with your customers yet" banner and the cards read it again. */
function markKnowledgeChanged(businessId: string): void {
  for (const prefix of [queryKeys.profile.all(businessId), queryKeys.knowledge.all(businessId), queryKeys.business.all(businessId), queryKeys.resources.all(businessId)]) {
    invalidate(prefix, { refetchActive: false });
  }
}

export function SectionEditor({ section }: { section: ProfileSection }) {
  const { t } = useI18n();
  const router = useRouter();
  const { business, isOwner, isPlatformAdmin } = useBusiness();
  const canEdit = isOwner || isPlatformAdmin;
  const data = useSetupData(business.id, canEdit);
  const { setup, starters, wizard, refresh } = data;
  const onSaved = useCallback(() => markKnowledgeChanged(business.id), [business.id]);

  const ctx = useMemo<StepContext | null>(() => {
    if (!setup.data || !starters.data || !wizard.data) {
      return null;
    }
    const toCards = () => router.push(profilePath(business.id));
    return {
      businessId: business.id,
      setup: setup.data,
      starters: starters.data,
      wizard: wizard.data,
      refresh,
      next: toCards,
      back: toCards,
      goTo: toCards,
      skip: async () => undefined,
    };
  }, [business.id, refresh, router, setup.data, starters.data, wizard.data]);

  if (!canEdit) {
    return <Alert tone="info">{t("profileEdit.ownerOnly")}</Alert>;
  }
  const error = (!setup.data && setup.error) || (!starters.data && starters.error) || (!wizard.data && wizard.error);
  if (error) {
    return (
      <ErrorState
        error={error}
        onRetry={() => {
          setup.reload();
          starters.reload();
          wizard.reload();
        }}
      />
    );
  }
  if (!ctx) {
    return (
      <LoadingRegion label={t("common.loading")}>
        <SectionEditorSkeleton />
      </LoadingRegion>
    );
  }
  const Screen = SCREENS[section];
  return (
    <SaveTrackerProvider onSaved={onSaved}>
      {(state) => (
        <div className="space-y-8">
          <EditorBar businessId={business.id} state={state} />
          <Screen ctx={ctx} />
        </div>
      )}
    </SaveTrackerProvider>
  );
}
