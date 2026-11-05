/** The drafts of one menu import under review, and how ticking, ticking all and editing change them. */

import type { KnowledgeItemDetails, Schema } from "@/api/types";
import { initialImportSelection, type ImportedMenuItem } from "@/lib/knowledge/menuImport";

export interface ImportReview {
  /** The import: discarding it deletes every draft not confirmed. */
  batchId: string;
  items: ImportedMenuItem[];
  skipped: number;
  selected: ReadonlySet<string>;
}

/** The review of a fresh import: the drafts the reader was fairly sure of are ticked. */
export function reviewOfImport(data: Schema<"MenuImportResult">): ImportReview {
  const items = data.items ?? [];
  return {
    batchId: data.batch_id,
    items,
    skipped: data.skipped_line_count ?? 0,
    selected: initialImportSelection(items),
  };
}

export function withDraftTicked(review: ImportReview, id: string, checked: boolean): ImportReview {
  const selected = new Set(review.selected);
  if (checked) {
    selected.add(id);
  } else {
    selected.delete(id);
  }
  return { ...review, selected };
}

export function withAllDraftsTicked(review: ImportReview, checked: boolean): ImportReview {
  return { ...review, selected: checked ? new Set(review.items.map((item) => item.item.id)) : new Set() };
}

/** The review after the owner fixed a draft in the editor. */
export function withSavedDraft(review: ImportReview, saved: KnowledgeItemDetails): ImportReview {
  return {
    ...review,
    items: review.items.map((entry) =>
      entry.item.id === saved.id
        ? {
            ...entry,
            is_currency_mismatch: entry.is_currency_mismatch && (saved.price_minor === null || saved.price_minor === undefined),
            item: {
              id: saved.id,
              kind: saved.kind,
              title: saved.title,
              body: saved.body,
              price_minor: saved.price_minor,
              currency_code: saved.currency_code,
              duration_minutes: saved.duration_minutes,
              formatted_price: saved.formatted_price,
              tags: saved.tags,
            },
          }
        : entry,
    ),
  };
}
