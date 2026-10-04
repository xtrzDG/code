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

export const contentEn = {
  knowledge: { ...knowledgeEn, ...knowledgeResourcesEn, ...knowledgeWebsiteEn, ...knowledgeOfferEn },
  assistant: { ...assistantEn, ...assistantChecksEn, ...assistantChatEn },
} as const;

export const contentRu: Translation<typeof contentEn> = {
  knowledge: { ...knowledgeRu, ...knowledgeResourcesRu, ...knowledgeWebsiteRu, ...knowledgeOfferRu },
  assistant: { ...assistantRu, ...assistantChecksRu, ...assistantChatRu },
};

export const contentKa: Translation<typeof contentEn> = {
  knowledge: { ...knowledgeKa, ...knowledgeResourcesKa, ...knowledgeWebsiteKa, ...knowledgeOfferKa },
  assistant: { ...assistantKa, ...assistantChecksKa, ...assistantChatKa },
};
