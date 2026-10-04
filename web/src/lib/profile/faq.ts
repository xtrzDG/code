/**
 * The business's ready answers (knowledge items of kind "faq") as lines of
 * the profile editor: in the order the owner added them, each saved by
 * itself once it has both a question and an answer.
 */

import type { KnowledgeItemDetails, RequestBody } from "@/api/types";

import { faqRowFromItem, isFaqRowChanged, validateFaqRow, type FaqRow } from "../wizard/faq";

export type FaqSave =
  | { kind: "none" }
  | { kind: "invalid" }
  | { kind: "create"; body: RequestBody<"/v1/businesses/{business_id}/knowledge", "post"> }
  | { kind: "update"; id: string; body: RequestBody<"/v1/businesses/{business_id}/knowledge/{item_id}", "patch"> };

/** The business's active ready answers, oldest first (the API lists the newest first). */
export function faqRowsFrom(items: readonly KnowledgeItemDetails[]): FaqRow[] {
  return items
    .filter((item) => item.kind === "faq" && item.is_active)
    .sort((left, right) => left.created_at - right.created_at || left.id.localeCompare(right.id))
    .map(faqRowFromItem);
}

/** What saving a line means now: nothing, not yet (a question without its answer), a new item or a change. */
export function faqSave(row: FaqRow): FaqSave {
  const question = row.question.trim();
  const answer = row.answer.trim();
  if ((question === "" && answer === "") || !isFaqRowChanged(row)) {
    return { kind: "none" };
  }
  if (Object.keys(validateFaqRow(row)).length > 0) {
    return { kind: "invalid" };
  }
  return row.id ? { kind: "update", id: row.id, body: { title: question, body: answer } } : { kind: "create", body: { kind: "faq", title: question, body: answer, is_active: true } };
}

/**
 * The line after the API stored it: its id, and the stored text as the new
 * baseline unless the owner typed on while it was being saved.
 */
export function savedFaqRow(row: FaqRow, item: KnowledgeItemDetails): FaqRow {
  const stored = faqRowFromItem(item);
  const typed = { ...stored, question: row.question, answer: row.answer };
  return { ...row, id: item.id, baseline: isFaqRowChanged(typed) ? stored.baseline : typed.baseline };
}
