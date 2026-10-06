/**
 * Texts of the cabinet sections: Knowledge base and the assistant (test chat, versions, autotests, publishing).
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts, ru.ts and ka.ts, so they must not clash with the
 * namespaces of the other dictionaries. `ru` and `ka` are type-checked
 * against `en`.
 *
 * Each namespace (a large one in a few parts) lives in its own file per
 * language under `./content/`; this file composes them.
 */

import type { Translation } from "../../translate";
import { assistantEn } from "./content/assistant.en";
import { assistantKa } from "./content/assistant.ka";
import { assistantRu } from "./content/assistant.ru";
import { assistantChatEn } from "./content/assistantChat.en";
import { assistantChatKa } from "./content/assistantChat.ka";
import { assistantChatRu } from "./content/assistantChat.ru";
import { assistantChecksEn } from "./content/assistantChecks.en";
import { assistantChecksKa } from "./content/assistantChecks.ka";
import { assistantChecksRu } from "./content/assistantChecks.ru";
import { assistantComparisonEn } from "./content/assistantComparison.en";
import { assistantComparisonKa } from "./content/assistantComparison.ka";
import { assistantComparisonRu } from "./content/assistantComparison.ru";
import { knowledgeEn } from "./content/knowledge.en";
import { knowledgeKa } from "./content/knowledge.ka";
import { knowledgeRu } from "./content/knowledge.ru";
import { knowledgeOfferEn } from "./content/knowledgeOffer.en";
import { knowledgeOfferKa } from "./content/knowledgeOffer.ka";
import { knowledgeOfferRu } from "./content/knowledgeOffer.ru";
import { knowledgeResourcesEn } from "./content/knowledgeResources.en";
import { knowledgeResourcesKa } from "./content/knowledgeResources.ka";
import { knowledgeResourcesRu } from "./content/knowledgeResources.ru";
import { knowledgeWebsiteEn } from "./content/knowledgeWebsite.en";
import { knowledgeWebsiteKa } from "./content/knowledgeWebsite.ka";
import { knowledgeWebsiteRu } from "./content/knowledgeWebsite.ru";
import { assistantHe } from "./content/assistant.he";
import { assistantDe } from "./content/assistant.de";
import { assistantChatHe } from "./content/assistantChat.he";
import { assistantChatDe } from "./content/assistantChat.de";
import { assistantChecksHe } from "./content/assistantChecks.he";
import { assistantChecksDe } from "./content/assistantChecks.de";
import { assistantComparisonHe } from "./content/assistantComparison.he";
import { assistantComparisonDe } from "./content/assistantComparison.de";
import { knowledgeHe } from "./content/knowledge.he";
import { knowledgeDe } from "./content/knowledge.de";
import { knowledgeOfferHe } from "./content/knowledgeOffer.he";
import { knowledgeOfferDe } from "./content/knowledgeOffer.de";
import { knowledgeResourcesHe } from "./content/knowledgeResources.he";
import { knowledgeResourcesDe } from "./content/knowledgeResources.de";
import { knowledgeWebsiteHe } from "./content/knowledgeWebsite.he";
import { knowledgeWebsiteDe } from "./content/knowledgeWebsite.de";

export const contentEn = {
  knowledge: { ...knowledgeEn, ...knowledgeResourcesEn, ...knowledgeWebsiteEn, ...knowledgeOfferEn },
  assistant: { ...assistantEn, ...assistantChecksEn, ...assistantComparisonEn, ...assistantChatEn },
} as const;

export const contentRu: Translation<typeof contentEn> = {
  knowledge: { ...knowledgeRu, ...knowledgeResourcesRu, ...knowledgeWebsiteRu, ...knowledgeOfferRu },
  assistant: { ...assistantRu, ...assistantChecksRu, ...assistantComparisonRu, ...assistantChatRu },
};

export const contentKa: Translation<typeof contentEn> = {
  knowledge: { ...knowledgeKa, ...knowledgeResourcesKa, ...knowledgeWebsiteKa, ...knowledgeOfferKa },
  assistant: { ...assistantKa, ...assistantChecksKa, ...assistantComparisonKa, ...assistantChatKa },
};

export const contentHe: Translation<typeof contentEn> = {
  knowledge: { ...knowledgeHe, ...knowledgeResourcesHe, ...knowledgeWebsiteHe, ...knowledgeOfferHe },
  assistant: { ...assistantHe, ...assistantChecksHe, ...assistantComparisonHe, ...assistantChatHe },
};

export const contentDe: Translation<typeof contentEn> = {
  knowledge: { ...knowledgeDe, ...knowledgeResourcesDe, ...knowledgeWebsiteDe, ...knowledgeOfferDe },
  assistant: { ...assistantDe, ...assistantChecksDe, ...assistantComparisonDe, ...assistantChatDe },
};
