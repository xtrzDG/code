import type { Locale } from "../config";
import { mergeMessages, type MessageTree } from "../translate";
import { en } from "./en";
import { ka } from "./ka";
import { ru } from "./ru";

export const DICTIONARIES: Record<Locale, MessageTree> = { en, ru, ka };

export const FALLBACK_MESSAGES: MessageTree = en;

/** The dictionary of a language with English filled in for missing texts. */
export function getMessages(locale: Locale): MessageTree {
  return locale === "en" ? en : mergeMessages(en, DICTIONARIES[locale]);
}
