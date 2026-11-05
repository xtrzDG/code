"use client";

/**
 * Assistant → Business profile: six cards, one per section of what the
 * assistant knows (the business, its place, its offer, hours and
 * bookings, the people who help, the rules), each with a line of what it
 * holds and what is left to add. A card opens the section's editor, the
 * same screen as in "Create an AI assistant", saving as the owner types.
 */

import { Stagger, StaggerItem } from "@/components/motion";
import { useBusiness } from "@/components/business/BusinessContext";
import { ErrorState, PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { gapsBySection, PROFILE_SECTIONS, profileSectionPath } from "@/lib/profile/sections";

import { SectionCard } from "./_components/SectionCard";
import { useProfileData } from "./_components/useProfileData";
import { sectionSummary } from "./_lib/sectionSummaries";

export function ProfileOverview() {
  const translator = useI18n();
  const { t } = translator;
  const { business } = useBusiness();
  const { wizard, knowledge, gaps } = useProfileData(business.id);
  const gapCounts = gaps.data ? gapsBySection(gaps.data.gaps ?? []) : undefined;
  const input = { business, wizard: wizard.data, items: knowledge.data?.items };
  const error = (!wizard.data && wizard.error) || (!knowledge.data && knowledge.error);

  return (
    <>
      <PageHeader title={t("profileEdit.title")} description={t("profileEdit.description")} />
      {error ? (
        <ErrorState
          error={error}
          onRetry={() => {
            wizard.reload();
            knowledge.reload();
          }}
        />
      ) : (
        <Stagger as="ul" tone="cabinet" onMount aria-label={t("profileEdit.cardsLabel")} className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {PROFILE_SECTIONS.map((section) => (
            <StaggerItem as="li" tone="cabinet" key={section} className="min-w-0">
              <SectionCard
                section={section}
                href={profileSectionPath(business.id, section)}
                summary={sectionSummary(section, input, translator)}
                gaps={gapCounts?.[section]}
              />
            </StaggerItem>
          ))}
        </Stagger>
      )}
    </>
  );
}
