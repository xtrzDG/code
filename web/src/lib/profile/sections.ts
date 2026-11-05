/**
 * Assistant → Business profile as data: the six sections a live owner
 * edits (the same screens as "Create an AI assistant", in an edit mode
 * that saves as the owner types), where each one lives, which of the
 * niche's questions it asks, and where the old six-step profile's
 * addresses (`?step=offer`) and the "what to add" items lead now.
 */

import type { Schema } from "@/api/types";

import { businessPath } from "../navigation";

export const PROFILE_SECTIONS = ["business", "place", "offer", "hours", "people", "rules"] as const;

export type ProfileSection = (typeof PROFILE_SECTIONS)[number];

type ProfileWizardStep = Schema<"ProfileWizardStep">;
type WizardQuestionView = Schema<"WizardQuestionView">;
type ProfileGap = Schema<"ProfileGap">;
type ProfileGapKind = Schema<"ProfileGapKind">;

export function isProfileSection(value: string | null | undefined): value is ProfileSection {
  return (PROFILE_SECTIONS as readonly string[]).includes(value ?? "");
}

/** The cards page: /b/{id}/assistant/profile. */
export function profilePath(businessId: string): string {
  return businessPath(businessId, "assistant/profile");
}

/** One section's editor: /b/{id}/assistant/profile/{section}. */
export function profileSectionPath(businessId: string, section: ProfileSection): string {
  return `${profilePath(businessId)}/${section}`;
}

/** Where each step of the old six-step profile (and its niche questions) is edited now. */
export const SECTION_OF_STEP: Readonly<Record<ProfileWizardStep, ProfileSection>> = {
  niche_and_languages: "business",
  contacts_and_hours: "hours",
  offer: "offer",
  booking_rules: "hours",
  faq_and_handoff: "rules",
  channels: "business",
};

/** The niche questions each section asks, by the profile step they belong to. */
export function questionStepsOf(section: ProfileSection): ReadonlySet<ProfileWizardStep> {
  return new Set((Object.keys(SECTION_OF_STEP) as ProfileWizardStep[]).filter((step) => SECTION_OF_STEP[step] === section));
}

/** The section's niche questions with their answers, in the profile's order. */
export function sectionQuestions(wizard: { steps: readonly Pick<Schema<"WizardStepView">, "questions">[] }, section: ProfileSection): WizardQuestionView[] {
  const steps = questionStepsOf(section);
  return wizard.steps.flatMap((step) => step.questions ?? []).filter((item) => steps.has(item.question.step));
}

/**
 * The section an old address opens (`?step=booking_rules` → hours), or
 * null when the step is not one of the old profile's.
 */
export function sectionOfStepParam(step: string | string[] | null | undefined): ProfileSection | null {
  const value = Array.isArray(step) ? step[0] : step;
  if (!value || !Object.hasOwn(SECTION_OF_STEP, value)) {
    return null;
  }
  return SECTION_OF_STEP[value as ProfileWizardStep];
}

/** Where each kind of "what to add" item is fixed (a missing answer: where its question is). */
const SECTION_OF_GAP: Readonly<Record<Exclude<ProfileGapKind, "missing_required_answer">, ProfileSection>> = {
  no_opening_hours: "hours",
  no_address: "place",
  no_handoff_contact: "people",
  no_booking_rules: "hours",
  no_resources: "hours",
  no_priced_items: "offer",
  no_faq: "rules",
  unanswered_question: "rules",
};

export function sectionOfGap(gap: Pick<ProfileGap, "kind" | "step">): ProfileSection {
  return gap.kind === "missing_required_answer" ? SECTION_OF_STEP[gap.step] : SECTION_OF_GAP[gap.kind];
}

export interface SectionGaps {
  /** Must be filled before the assistant can be prepared. */
  blocking: number;
  /** Would make its answers better (customers' unanswered questions among them). */
  advice: number;
}

/** How many "what to add" items each section has. */
export function gapsBySection(gaps: readonly Pick<ProfileGap, "kind" | "step" | "is_blocking">[]): Record<ProfileSection, SectionGaps> {
  const counts = Object.fromEntries(PROFILE_SECTIONS.map((section) => [section, { blocking: 0, advice: 0 }])) as Record<ProfileSection, SectionGaps>;
  for (const gap of gaps) {
    const count = counts[sectionOfGap(gap)];
    if (gap.is_blocking) {
      count.blocking += 1;
    } else {
      count.advice += 1;
    }
  }
  return counts;
}
