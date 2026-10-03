/**
 * Quick replies (saved replies of a business): the variables their texts
 * may carry, finding and filling them, and the shortcut rule. Shared by
 * Settings → Quick replies (the owner's editor) and the reply box of a
 * conversation, where the API has already filled what it knows.
 */

import type { Schema } from "@/api/types";

export type QuickReplyVariable = Schema<"QuickReplyVariable">;

/** Every variable the API fills, in the order the editor offers them. */
export const QUICK_REPLY_VARIABLES = ["name", "booking_time", "business_name"] as const satisfies readonly QuickReplyVariable[];

/** The shortest and longest shortcut, and its characters: letters of any script, digits, "_" and "-". */
export const SHORTCUT_MAX_LENGTH = 32;
const SHORTCUT_PATTERN = /^[\p{L}\p{N}\p{M}_-]+$/u;

export const QUICK_REPLY_TITLE_MAX_LENGTH = 80;
export const QUICK_REPLY_TEXT_MAX_LENGTH = 2000;

export function isValidShortcut(shortcut: string): boolean {
  return shortcut.length >= 1 && shortcut.length <= SHORTCUT_MAX_LENGTH && SHORTCUT_PATTERN.test(shortcut);
}

/** "{name}" for a variable. */
export function placeholderOf(variable: QuickReplyVariable): string {
  return `{${variable}}`;
}

/** The known variables still in braces in a text, in order of first appearance. */
export function placeholdersIn(text: string): QuickReplyVariable[] {
  const found: QuickReplyVariable[] = [];
  for (const match of text.matchAll(/\{(\w+)\}/g)) {
    const name = match[1] as QuickReplyVariable;
    if ((QUICK_REPLY_VARIABLES as readonly string[]).includes(name) && !found.includes(name)) {
      found.push(name);
    }
  }
  return found;
}

/** The text with every "{variable}" replaced by the value (trimmed; an empty value changes nothing). */
export function fillPlaceholder(text: string, variable: QuickReplyVariable, value: string): string {
  const filled = value.trim();
  return filled ? text.split(placeholderOf(variable)).join(filled) : text;
}

/** The text as a customer would read it, with example values for the variables. */
export function previewQuickReply(text: string, values: Readonly<Record<QuickReplyVariable, string>>): string {
  return QUICK_REPLY_VARIABLES.reduce((result, variable) => fillPlaceholder(result, variable, values[variable]), text);
}

/** The text with `insert` put at the caret (or in place of the selection), and where the caret goes next. */
export function insertAt(text: string, insert: string, start: number, end: number = start): { text: string; caret: number } {
  const from = Math.max(0, Math.min(start, text.length));
  const to = Math.max(from, Math.min(end, text.length));
  return { text: `${text.slice(0, from)}${insert}${text.slice(to)}`, caret: from + insert.length };
}
