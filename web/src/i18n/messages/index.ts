import type { Locale } from "../config";
import { mergeMessages, type MessageTree } from "../translate";
import { de } from "./de";
import { en } from "./en";
import { he } from "./he";
import { ka } from "./ka";
import { ru } from "./ru";

export const DICTIONARIES: Record<Locale, MessageTree> = { en, ru, ka, he, de };

export const FALLBACK_MESSAGES: MessageTree = en;

/** The dictionary of a language with English filled in for missing texts. */
export function getMessages(locale: Locale): MessageTree {
  return locale === "en" ? en : mergeMessages(en, DICTIONARIES[locale]);
}
