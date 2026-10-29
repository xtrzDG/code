/**
 * The texts of the platform's default privacy notice for a business's chat
 * (/c/{address}/privacy). English is the reviewed cabinet text
 * (`privacyNotice.*`); every other language of the chat widget has its
 * text here: Russian and Georgian reviewed (the cabinet texts they were),
 * the rest drafts marked `needs_review` until a translator and a lawyer
 * have checked them. A draft says so on the page and links to the English
 * text, which prevails.
 */

import type { privacyNoticeEn } from "@/i18n/messages/sections/workspace/privacyNotice.en";

type PrivacyNoticeKey = keyof typeof privacyNoticeEn;

export type PrivacyNoticeTexts = Record<PrivacyNoticeKey, string> & {
  /** "This translation is a draft…": shown above a draft. */
  draftNote: string;
  /** The link to the English text under that note. */
  readInEnglish: string;
};

type ReviewStatus = "needs_review" | "reviewed";

export interface PrivacyNoticeDraft {
  status: ReviewStatus;
  texts: PrivacyNoticeTexts;
}
