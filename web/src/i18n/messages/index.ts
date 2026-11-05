import type { Locale } from "../config";
import { mergeMessages, type MessageTree } from "../translate";
import { en } from "./en";
import { it } from "./it";

export const DICTIONARIES: Record<Locale, MessageTree> = { en, it };

export const FALLBACK_MESSAGES: MessageTree = en;

/** The dictionary of a language with English filled in for missing texts. */
export function getMessages(locale: Locale): MessageTree {
  return locale === "en" ? en : mergeMessages(en, DICTIONARIES[locale]);
}
