/**
 * Texts customers read around the chat: the hosted chat page (/c/{address})
 * while the chat opens or when it cannot, and the printable table card.
 * They are in the languages of the website chat widget (any business
 * language), not only the cabinet's ka/ru/en, so they live here instead
 * of the cabinet dictionaries. A language without texts falls back to
 * English.
 */

import { primaryLanguage } from "./language";
import { TEXTS_ASIA } from "./textsAsia";
import { TEXTS_EUROPE } from "./textsEurope";

export interface HostedChatTexts {
  /** Under the spinner until the chat appears. */
  loading: string;
  /** The chat is switched off or could not be loaded. */
  unavailable: string;
  tryLater: string;
  /** Without JavaScript the chat cannot work. */
  noScript: string;
  /** Nothing at this address. */
  notFound: string;
  /** The table card's heading above the QR code. */
  scanToChat: string;
  /** The table card's line under the heading. */
  cardHint: string;
}

export const HOSTED_CHAT_TEXTS: Readonly<Record<string, HostedChatTexts>> = { ...TEXTS_EUROPE, ...TEXTS_ASIA };

/** The languages with texts, for language pickers: "en", "ka", "he"... */
export const HOSTED_CHAT_LANGUAGES: readonly string[] = Object.keys(HOSTED_CHAT_TEXTS);

const ENGLISH = TEXTS_EUROPE.en as HostedChatTexts;

/** The texts of a language tag ("pt-BR" uses "pt"); English when there are none. */
export function hostedChatTexts(tag: string): HostedChatTexts {
  return HOSTED_CHAT_TEXTS[primaryLanguage(tag)] ?? ENGLISH;
}

/** True when `tag` has texts of its own (not the English fallback). */
export function hasHostedChatTexts(tag: string): boolean {
  return primaryLanguage(tag) in HOSTED_CHAT_TEXTS;
}
