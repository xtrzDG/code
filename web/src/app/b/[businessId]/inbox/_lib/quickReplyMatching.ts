/**
 * Pure rules of the quick-reply picker: when the reply box asks for it
 * ("/" then a word, nothing else), and which replies match what was typed
 * (shortcut first, then name and text, without case or accents).
 */

import type { FilledQuickReplyView } from "./types";

const SLASH_COMMAND = /^\/([\p{L}\p{N}\p{M}_-]*)$/u;

/** The word after "/" when the whole text is a picker command ("/hours" -> "hours"), else null. */
export function slashQuery(draft: string): string | null {
  const match = SLASH_COMMAND.exec(draft.trimStart());
  return match ? (match[1] ?? "") : null;
}

/** Lower case without accents, for matching "cafe" with "Café". */
function folded(text: string): string {
  return text.normalize("NFD").replace(/\p{M}/gu, "").toLocaleLowerCase();
}

/**
 * The replies that match the query, best first: the shortcut starts with
 * it, then the shortcut or the name contains it, then the text does.
 * An empty query lists every reply in the owner's order.
 */
export function matchQuickReplies(replies: readonly FilledQuickReplyView[], query: string): FilledQuickReplyView[] {
  const wanted = folded(query.trim());
  if (!wanted) {
    return [...replies];
  }
  const ranked = replies
    .map((reply, order) => {
      const shortcut = folded(reply.shortcut);
      const rank = shortcut.startsWith(wanted)
        ? 0
        : shortcut.includes(wanted) || folded(reply.title).includes(wanted)
          ? 1
          : folded(reply.text).includes(wanted)
            ? 2
            : null;
      return { reply, order, rank };
    })
    .filter((entry): entry is { reply: FilledQuickReplyView; order: number; rank: number } => entry.rank !== null);
  return ranked.sort((left, right) => left.rank - right.rank || left.order - right.order).map((entry) => entry.reply);
}
