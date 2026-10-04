/**
 * The lines each card of Assistant → Business profile shows about its
 * section, in the owner's words: "Mtsvane Ezo · Restaurants and cafés",
 * "Mon–Sun 10:00–23:00 · up to 12 people per booking", "24 items · 18
 * with a price", and so on. Null while what a line needs is loading.
 */

import type { BusinessView, KnowledgeItemDetails, ProfileWizardView } from "@/api/types";
import type { Translator } from "@/i18n/translate";
import { languageName } from "@/lib/format";
import { listFormat } from "@/lib/intl/formatters";
import type { ProfileSection } from "@/lib/profile/sections";
import { knowledgeCounts, weekSummary } from "@/lib/profile/summary";

type Words = Pick<Translator, "t" | "tp" | "locale">;

export interface SummaryInput {
  business: BusinessView;
  wizard: ProfileWizardView | undefined;
  items: readonly KnowledgeItemDetails[] | undefined;
}

const joined = (parts: readonly (string | null | undefined | false)[]) => parts.filter(Boolean).join(" · ");

export function sectionSummary(section: ProfileSection, input: SummaryInput, words: Words): string | null {
  const { t, tp, locale } = words;
  const { business, wizard, items } = input;
  const profile = wizard?.profile;
  switch (section) {
    case "business":
      return joined([business.name, wizard?.niche.name]);
    case "place":
      return profile
        ? joined([
            profile.address?.text ?? t("profileEdit.summary.noAddress"),
            business.languages.map((tag) => languageName(tag, locale)).join(", "),
          ])
        : null;
    case "offer": {
      if (!items) {
        return null;
      }
      const counts = knowledgeCounts(items);
      return counts.offers === 0 ? t("profileEdit.summary.noOffer") : joined([tp("profileEdit.summary.offer", counts.offers), tp("profileEdit.summary.priced", counts.priced)]);
    }
    case "hours": {
      if (!wizard || !profile) {
        return null;
      }
      const week = weekSummary(profile.hours ?? [], locale, t("profileEdit.summary.roundTheClock")) || t("profileEdit.summary.noHours");
      const rules = profile.booking_rules;
      return joined([week, wizard.niche.takes_bookings && rules ? tp("profileEdit.summary.partySize", rules.max_party_size) : null]);
    }
    case "people": {
      const names = [...new Set((business.manager_contacts ?? []).map((contact) => contact.name))];
      return names.length > 0 ? listFormat(locale, { type: "conjunction" }).format(names) : t("profileEdit.summary.noPeople");
    }
    case "rules":
      return profile && items
        ? joined([
            tp("profileEdit.summary.answers", knowledgeCounts(items).questions),
            tp("profileEdit.summary.handoff", (profile.handoff_rules ?? []).length),
            tp("profileEdit.summary.forbidden", (profile.forbidden ?? []).length),
          ])
        : null;
  }
}
