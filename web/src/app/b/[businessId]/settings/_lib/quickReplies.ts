/**
 * Settings → Quick replies: the editor's draft of one reply (a text per
 * language of the business), checking it, and the API body it becomes.
 */

import {
  isValidShortcut,
  QUICK_REPLY_TEXT_MAX_LENGTH,
  QUICK_REPLY_TITLE_MAX_LENGTH,
  SHORTCUT_MAX_LENGTH,
  type QuickReplyBody,
  type QuickReplyView,
} from "@/lib/quickReplies";

export interface QuickReplyDraft {
  title: string;
  shortcut: string;
  /** The text per language code ("" for a language left out). */
  texts: Record<string, string>;
}

export type QuickReplyDraftError = "title" | "shortcut" | "texts" | "tooLong";

/**
 * The languages the editor offers: the business's, its default first, then
 * any language the reply already has that the business no longer lists.
 */
export function editorLanguages(
  businessLanguages: readonly string[],
  defaultLanguage: string,
  reply: QuickReplyView | null,
): string[] {
  const ordered = [defaultLanguage, ...businessLanguages.filter((language) => language !== defaultLanguage)];
  const extra = (reply?.variants ?? []).map((variant) => variant.language).filter((language) => !ordered.includes(language));
  return [...ordered, ...extra];
}

/** The draft of a new reply, or of the reply being edited. */
export function draftOf(reply: QuickReplyView | null, languages: readonly string[]): QuickReplyDraft {
  const texts = Object.fromEntries(languages.map((language) => [language, ""]));
  for (const variant of reply?.variants ?? []) {
    texts[variant.language] = variant.text;
  }
  return { title: reply?.title ?? "", shortcut: reply?.shortcut ?? "", texts };
}

/** A shortcut as typed, without the leading "/" and spaces. */
export function cleanShortcut(text: string): string {
  return text.replace(/^\/+/, "").replace(/\s+/g, "").slice(0, SHORTCUT_MAX_LENGTH);
}

/** What keeps the draft from being saved, in the order of the form; empty when it can be. */
export function draftErrors(draft: QuickReplyDraft): QuickReplyDraftError[] {
  const errors: QuickReplyDraftError[] = [];
  const title = draft.title.trim();
  if (!title || title.length > QUICK_REPLY_TITLE_MAX_LENGTH) {
    errors.push("title");
  }
  if (!isValidShortcut(draft.shortcut)) {
    errors.push("shortcut");
  }
  const texts = Object.values(draft.texts);
  if (!texts.some((text) => text.trim())) {
    errors.push("texts");
  }
  if (texts.some((text) => text.length > QUICK_REPLY_TEXT_MAX_LENGTH)) {
    errors.push("tooLong");
  }
  return errors;
}

/** The body of POST/PUT …/quick-replies: the languages with a text, in the editor's order. */
export function bodyOf(draft: QuickReplyDraft, languages: readonly string[]): QuickReplyBody {
  return {
    title: draft.title.trim(),
    shortcut: draft.shortcut,
    variants: languages
      .filter((language) => (draft.texts[language] ?? "").trim())
      .map((language) => ({ language, text: (draft.texts[language] ?? "").trim() })),
  };
}
