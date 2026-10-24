/**
 * The Instagram card's replies to comments as a form: keywords (distinct,
 * one line each), the message in Direct, and the PUT body. The API checks
 * the same rules (backend InstagramCommentRepliesRequest).
 */

import type { RequestBody, Schema } from "@/api/types";

export type CommentRepliesView = Schema<"InstagramCommentRepliesView">;
export type CommentRepliesBody = RequestBody<"/v1/businesses/{business_id}/channels/instagram/comment-replies", "put">;

export const MAX_KEYWORDS = 20;
const MAX_KEYWORD_LENGTH = 50;
export const MAX_REPLY_LENGTH = 1000;

export interface CommentRepliesForm {
  isOn: boolean;
  keywords: string[];
  replyText: string;
}

export function commentRepliesForm(view: CommentRepliesView): CommentRepliesForm {
  return { isOn: view.is_on, keywords: [...(view.keywords ?? [])], replyText: view.reply_text ?? "" };
}

export type KeywordProblem = "keyword" | "tooMany";

const sameWord = (left: string, right: string) => left.toLocaleLowerCase() === right.toLocaleLowerCase();

/**
 * The keywords with one more typed in: trimmed, inner spaces folded, kept
 * once (in any letter case); or why it cannot be added.
 */
export function addKeyword(keywords: readonly string[], typed: string): { keywords: string[]; problem: KeywordProblem | null } {
  const word = typed.replace(/\s+/g, " ").trim();
  if (word === "" || word.length > MAX_KEYWORD_LENGTH || /[\r\n]/.test(typed.trim())) {
    return { keywords: [...keywords], problem: "keyword" };
  }
  if (keywords.some((kept) => sameWord(kept, word))) {
    return { keywords: [...keywords], problem: null };
  }
  if (keywords.length >= MAX_KEYWORDS) {
    return { keywords: [...keywords], problem: "tooMany" };
  }
  return { keywords: [...keywords, word], problem: null };
}

export type CommentRepliesProblem = "keywordsMissing" | "replyMissing";

export type CommentRepliesResult =
  | { ok: true; body: CommentRepliesBody }
  | { ok: false; problems: CommentRepliesProblem[] };

/** The PUT body, or what to fix first: turned on, it needs a keyword and a message. */
export function buildCommentRepliesBody(form: CommentRepliesForm): CommentRepliesResult {
  const replyText = form.replyText.trim();
  if (form.isOn) {
    const problems: CommentRepliesProblem[] = [];
    if (form.keywords.length === 0) {
      problems.push("keywordsMissing");
    }
    if (replyText === "") {
      problems.push("replyMissing");
    }
    if (problems.length > 0) {
      return { ok: false, problems };
    }
  }
  return {
    ok: true,
    body: { is_on: form.isOn, keywords: form.keywords, reply_text: replyText === "" ? null : replyText },
  };
}

/** Whether the form holds what is saved (nothing to save). */
export function isSavedReplies(form: CommentRepliesForm, view: CommentRepliesView): boolean {
  const saved = commentRepliesForm(view);
  return (
    form.isOn === saved.isOn &&
    form.replyText.trim() === saved.replyText &&
    form.keywords.length === saved.keywords.length &&
    form.keywords.every((word, index) => word === saved.keywords[index])
  );
}
