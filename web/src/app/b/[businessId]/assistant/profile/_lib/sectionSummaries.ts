/**
 * The lines each card of Assistant → Business profile shows about its
 * section, in the owner's words: "Mtsvane Ezo · Restaurants and cafés",
 * "Mon–Sun 10:00–23:00 · up to 12 people per booking", "24 items · 18
 * with a price", and so on. Null while what a line needs is loading. The
 * business's own words in a line (its name, address, people) stay apart
 * as user content (`UserSentence`).
 */

import type { BusinessView, KnowledgeItemDetails, ProfileWizardView } from "@/api/types";
import type { Translator } from "@/i18n/translate";
import { interfaceSentence, joinSentences, userWords, type SentenceWithUserValues } from "@/i18n/userValues";
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

/** The parts that are there, " · " between them; the business's own words (`userWords`) stay apart as user content. */
function joined(parts: readonly (SentenceWithUserValues | string | null | undefined | false)[]): SentenceWithUserValues {
  const present = parts.filter((part): part is SentenceWithUserValues | string => Boolean(part));
  return joinSentences(
    present.map((part) => (typeof part === "string" ? interfaceSentence(part) : part)),
    " · ",
  );
}

export function sectionSummary(section: ProfileSection, input: SummaryInput, words: Words): SentenceWithUserValues | null {
  const { t, tp, locale } = words;
  const { business, wizard, items } = input;
  const profile = wizard?.profile;
  switch (section) {
    case "business":
      return joined([userWords(business.name), wizard?.niche.name]);
    case "place":
      return profile
        ? joined([
            profile.address?.text ? userWords(profile.address.text) : t("profileEdit.summary.noAddress"),
            business.languages.map((tag) => languageName(tag, locale)).join(", "),
          ])
        : null;
    case "offer": {
      if (!items) {
        return null;
      }
      const counts = knowledgeCounts(items);
      return counts.offers === 0
        ? interfaceSentence(t("profileEdit.summary.noOffer"))
        : joined([tp("profileEdit.summary.offer", counts.offers), tp("profileEdit.summary.priced", counts.priced)]);
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
      return names.length > 0
        ? userWords(listFormat(locale, { type: "conjunction" }).format(names))
        : interfaceSentence(t("profileEdit.summary.noPeople"));
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
