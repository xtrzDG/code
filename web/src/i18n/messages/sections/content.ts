/**
 * Texts of the cabinet sections: Knowledge base and the assistant (test chat, versions, autotests, publishing).
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts and it.ts, so they must not clash
 * with the namespaces of the other dictionaries. The other languages are
 * type-checked against `en`.
 *
 * Each namespace (a large one in a few parts) lives in its own file per
 * language under `./content/`; this file composes them.
 */

import type { Translation } from "../../translate";
import { assistantEn } from "./content/assistant.en";
import { assistantChatEn } from "./content/assistantChat.en";
import { assistantChecksEn } from "./content/assistantChecks.en";
import { assistantComparisonEn } from "./content/assistantComparison.en";
import { knowledgeAliasesEn } from "./content/knowledgeAliases.en";
import { knowledgeAliasesIt } from "./content/knowledgeAliases.it";
import { knowledgeEn } from "./content/knowledge.en";
import { knowledgeOfferEn } from "./content/knowledgeOffer.en";
import { knowledgeResourcesEn } from "./content/knowledgeResources.en";
import { knowledgeWebsiteEn } from "./content/knowledgeWebsite.en";
import { assistantIt } from "./content/assistant.it";
import { assistantChatIt } from "./content/assistantChat.it";
import { assistantChecksIt } from "./content/assistantChecks.it";
import { assistantComparisonIt } from "./content/assistantComparison.it";
import { knowledgeIt } from "./content/knowledge.it";
import { knowledgeOfferIt } from "./content/knowledgeOffer.it";
import { knowledgeResourcesIt } from "./content/knowledgeResources.it";
import { knowledgeWebsiteIt } from "./content/knowledgeWebsite.it";

export const contentEn = {
  knowledge: { ...knowledgeEn, ...knowledgeResourcesEn, ...knowledgeWebsiteEn, ...knowledgeOfferEn, ...knowledgeAliasesEn },
  assistant: { ...assistantEn, ...assistantChecksEn, ...assistantComparisonEn, ...assistantChatEn },
} as const;

export const contentIt: Translation<typeof contentEn> = {
  knowledge: { ...knowledgeIt, ...knowledgeResourcesIt, ...knowledgeWebsiteIt, ...knowledgeOfferIt, ...knowledgeAliasesIt },
  assistant: { ...assistantIt, ...assistantChecksIt, ...assistantComparisonIt, ...assistantChatIt },
};
