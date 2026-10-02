/**
 * Pure helpers of the profile wizard's FAQ step: question rows of the form,
 * their API body, and rule lists.
 */

import type { KnowledgeItemDetails } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

export interface FaqRow {
  key: string;
  id: string | null;
  question: string;
  answer: string;
  languages: string[];
  baseline: string | null;
}

function faqSnapshot(row: Pick<FaqRow, "question" | "answer">): string {
  return JSON.stringify([row.question.trim(), row.answer.trim()]);
}

export function faqRowFromItem(item: KnowledgeItemDetails): FaqRow {
  const row: FaqRow = {
    key: item.id,
    id: item.id,
    question: item.title,
    answer: item.body ?? "",
    languages: item.languages ?? [],
    baseline: null,
  };
  row.baseline = faqSnapshot(row);
  return row;
}

export function newFaqRow(key: string): FaqRow {
  return { key, id: null, question: "", answer: "", languages: [], baseline: null };
}

export function isFaqRowChanged(row: FaqRow): boolean {
  return row.baseline !== faqSnapshot(row);
}

export function validateFaqRow(row: FaqRow): { question?: MessageKey; answer?: MessageKey } {
  if (row.question.trim() === "" && row.answer.trim() === "") {
    return {};
  }
  return {
    ...(row.question.trim() === "" ? { question: "validation.required" as const } : {}),
    ...(row.answer.trim() === "" ? { answer: "validation.required" as const } : {}),
  };
}

export interface FaqEntryInput {
  id?: string | null;
  question: string;
  answer: string;
  languages?: string[];
}

export function faqPayload(rows: readonly FaqRow[]): FaqEntryInput[] {
  return rows
    .filter((row) => row.question.trim() !== "" && row.answer.trim() !== "" && isFaqRowChanged(row))
    .map((row) => ({
      ...(row.id ? { id: row.id } : {}),
      question: row.question.trim(),
      answer: row.answer.trim(),
      languages: row.languages,
    }));
}

export function markFaqRowsSaved(rows: readonly FaqRow[], saved: readonly KnowledgeItemDetails[]): FaqRow[] {
  return rows.map((row) => {
    if (row.question.trim() === "" || !isFaqRowChanged(row)) {
      return row;
    }
    const match = saved.find(
      (item) =>
        item.kind === "faq" &&
        ((row.id !== null && item.id === row.id) ||
          item.title.trim().toLocaleLowerCase() === row.question.trim().toLocaleLowerCase()),
    );
    return match ? { ...row, id: match.id, baseline: faqSnapshot(row) } : row;
  });
}

/** Rule lists without blanks and repeats. */
export function cleanRules(rules: readonly string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const rule of rules) {
    const trimmed = rule.trim();
    const key = trimmed.toLocaleLowerCase();
    if (trimmed !== "" && !seen.has(key)) {
      seen.add(key);
      result.push(trimmed);
    }
  }
  return result;
}
