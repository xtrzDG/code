"use client";

import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import type { KnowledgeItemDetails, Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { ImportedMenuItem } from "@/lib/knowledge/menuImport";

import type { KnowledgeEditorTarget } from "../../_components/KnowledgeItemEditor";
import {
  reviewOfImport,
  withAllDraftsTicked,
  withDraftTicked,
  withSavedDraft,
  type ImportReview,
} from "./importReview";

/**
 * Reviewing the drafts of a menu import: tick, fix in the editor, add the
 * ticked ones (the rest of the import is discarded in one request,
 * DELETE …/knowledge/import/{batch_id}) or discard them all.
 */
export function useImportReview() {
  const { t, tp } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();

  const [review, setReview] = useState<ImportReview | null>(null);
  const [editor, setEditor] = useState<{ key: number; target: KnowledgeEditorTarget } | null>(null);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [done, setDone] = useState<{ added: number } | null>(null);

  const confirm = useApiMutation((itemIds: string[]) =>
    api.POST("/v1/businesses/{business_id}/knowledge/import/confirm", {
      params: { path: { business_id: business.id } },
      body: { item_ids: itemIds },
    }),
  );
  const discardBatch = useApiMutation(
    (batchId: string) =>
      api.DELETE("/v1/businesses/{business_id}/knowledge/import/{batch_id}", {
        params: { path: { business_id: business.id, batch_id: batchId } },
      }),
    { errorToast: false },
  );

  // Leaving mid-review keeps the drafts switched off in the knowledge base: warn first.
  const isReviewing = review !== null && review.items.length > 0;
  useEffect(() => {
    if (!isReviewing) {
      return;
    }
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isReviewing]);

  const open = (result: Schema<"MenuImportResult">) => setReview(reviewOfImport(result));

  const addSelected = async () => {
    if (!review) {
      return;
    }
    const chosen = review.items.filter((item) => review.selected.has(item.item.id)).map((item) => item.item.id);
    const result = await confirm.run(chosen);
    if (!result.ok) {
      return;
    }
    // The confirmed items left the import; discarding it deletes the unticked rest.
    if (chosen.length < review.items.length) {
      const discarded = await discardBatch.run(review.batchId);
      if (!discarded.ok) {
        toast.show({ tone: "info", title: t("knowledge.import.someDraftsLeft") });
      }
    }
    toast.success(tp("knowledge.import.added", (result.data.activated_items ?? []).length));
    setDone({ added: (result.data.activated_items ?? []).length });
    setReview(null);
  };

  const discardAll = async () => {
    if (!review) {
      return;
    }
    const result = await discardBatch.run(review.batchId);
    setConfirmDiscard(false);
    if (!result.ok) {
      toast.show({ tone: "error", title: t("knowledge.import.discardFailed") });
      return;
    }
    toast.success(t("knowledge.import.discarded"));
    setReview(null);
  };

  /** Forget the import and what came of it. */
  const reset = () => {
    setDone(null);
    setReview(null);
  };

  const toggle = (id: string, checked: boolean) =>
    setReview((current) => (current ? withDraftTicked(current, id, checked) : current));
  const selectAll = (checked: boolean) =>
    setReview((current) => (current ? withAllDraftsTicked(current, checked) : current));
  const edit = (entry: ImportedMenuItem) =>
    setEditor((current) => ({
      key: (current?.key ?? 0) + 1,
      target: { mode: "edit", id: entry.item.id, item: { ...entry.item, is_active: false } },
    }));
  const saveDraft = (saved: KnowledgeItemDetails) => {
    setReview((current) => (current ? withSavedDraft(current, saved) : current));
    setEditor(null);
  };

  return {
    review,
    done,
    editor,
    closeEditor: () => setEditor(null),
    confirmDiscard,
    setConfirmDiscard,
    isSaving: confirm.isPending || discardBatch.isPending,
    isDiscarding: discardBatch.isPending,
    open,
    addSelected,
    discardAll,
    reset,
    toggle,
    selectAll,
    edit,
    saveDraft,
  };
}
