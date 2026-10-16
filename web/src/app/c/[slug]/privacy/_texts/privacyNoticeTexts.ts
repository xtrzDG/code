/**
 * The privacy notice of a hosted chat in a widget language: the reviewed
 * cabinet texts in the languages owners can choose, a draft marked
 * `needs_review` in the other languages of the chat widget (Hebrew and
 * German too while their cabinet texts await a native reviewer,
 * NEEDS_REVIEW_LOCALES), English for a language with neither.
 */

import { NEEDS_REVIEW_LOCALES, isCabinetLanguage } from "@/i18n/config";
import { getMessages } from "@/i18n/messages";
import { interpolate, lookupMessage, type MessageValues } from "@/i18n/translate";
import { primaryLanguage } from "@/lib/hostedChat/language";

import { DRAFTS_ASIA } from "./draftsAsia";
import { DRAFTS_CAUCASUS_TURKIC } from "./draftsCaucasusTurkic";
import { DRAFTS_EUROPE_NORTH_EAST } from "./draftsEuropeNorthEast";
import { DRAFTS_EUROPE_WEST } from "./draftsEuropeWest";
import { DRAFTS_MIDDLE_EAST } from "./draftsMiddleEast";
import type { PrivacyNoticeDraft, PrivacyNoticeTexts } from "./noticeTypes";

export const PRIVACY_NOTICE_DRAFTS: Readonly<Record<string, PrivacyNoticeDraft>> = {
  ...DRAFTS_EUROPE_WEST,
  ...DRAFTS_EUROPE_NORTH_EAST,
  ...DRAFTS_CAUCASUS_TURKIC,
  ...DRAFTS_MIDDLE_EAST,
  ...DRAFTS_ASIA,
};

const ENGLISH = "en";

export interface PrivacyNotice {
  /** The language the texts are in (the page's `lang`). */
  language: string;
  /** A draft not yet reviewed: the page says so and links to English. */
  needsReview: boolean;
  text: (key: keyof PrivacyNoticeTexts, values?: MessageValues) => string;
}

/** The notice in a language tag ("pt-BR" reads the "pt" draft). */
export function privacyNoticeFor(tag: string): PrivacyNotice {
  const language = primaryLanguage(tag);
  if (isCabinetLanguage(language) && !NEEDS_REVIEW_LOCALES.includes(language)) {
    const messages = getMessages(language);
    return {
      language,
      needsReview: false,
      text: (key, values) => {
        const template = lookupMessage(messages, `privacyNotice.${key}`);
        return interpolate(typeof template === "string" ? template : "", values);
      },
    };
  }
  const draft = PRIVACY_NOTICE_DRAFTS[language];
  if (!draft) {
    return privacyNoticeFor(ENGLISH);
  }
  return {
    language,
    needsReview: draft.status === "needs_review",
    text: (key, values) => interpolate(draft.texts[key], values),
  };
}
