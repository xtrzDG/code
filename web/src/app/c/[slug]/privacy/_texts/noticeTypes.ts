/**
 * The texts of the platform's default privacy notice for a business's chat
 * (/c/{address}/privacy). English, Russian and Georgian are the reviewed
 * cabinet texts (`privacyNotice.*`); every other language of the chat
 * widget has a draft here, marked `needs_review` until a translator and a
 * lawyer have checked it. A draft says so on the page and links to the
 * English text, which prevails.
 */

import type { privacyNoticeEn } from "@/i18n/messages/sections/workspace/privacyNotice.en";

export type PrivacyNoticeKey = keyof typeof privacyNoticeEn;

export type PrivacyNoticeTexts = Record<PrivacyNoticeKey, string> & {
  /** "This translation is a draft…": shown above a draft. */
  draftNote: string;
  /** The link to the English text under that note. */
  readInEnglish: string;
};

export type ReviewStatus = "needs_review" | "reviewed";

export interface PrivacyNoticeDraft {
  status: ReviewStatus;
  texts: PrivacyNoticeTexts;
}
