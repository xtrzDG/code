"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { unwrap } from "@/api/result";
import { sectionQueries } from "@/api/sectionQueries";
import type { KnowledgeItemDetails, KnowledgeItemKind, Schema } from "@/api/types";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { groupByKind, sortByTitle, type KnowledgeFilter } from "@/lib/knowledge/kinds";

import { useKnowledgeKinds } from "../_components/hooks";
import type { KnowledgeEditorTarget } from "../_components/KnowledgeItemEditor";
import { useKnowledgeToggle } from "./useKnowledgeToggle";

/** Open questions counted for the warning; more are shown as "more than". */
const QUESTIONS_ALERT_LIMIT = 100;

/**
 * The knowledge items list: paged and filtered by the API, grouped by kind
 * and sorted by title; switching items on and off, editing and deleting
 * them, and the open questions to warn about.
 */
export function useKnowledgeItems() {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const kinds = useKnowledgeKinds();

  const [filter, setFilter] = useState<KnowledgeFilter>({ kind: "all", status: "all" });
  const itemsQuery = sectionQueries.knowledgeItems(business.id, locale, filter.kind, filter.status);
  const items = useCursorPage<KnowledgeItemDetails, Schema<"KnowledgeItemPage">>(itemsQuery.key, itemsQuery.fetchPage, {
    pageSize: itemsQuery.pageSize,
  });
  const questions = useQuery(queryKeys.knowledge.questionsAlert(business.id), () =>
    api.GET("/v1/businesses/{business_id}/unanswered-questions", {
      params: { path: { business_id: business.id }, query: { limit: String(QUESTIONS_ALERT_LIMIT) } },
    }),
  );

  const [expanded, setExpanded] = useState<ReadonlySet<KnowledgeItemKind>>(new Set());
  const [editor, setEditor] = useState<{ key: number; target: KnowledgeEditorTarget } | null>(null);
  const [deleting, setDeleting] = useState<KnowledgeItemDetails | null>(null);
  const [hasChanges, setHasChanges] = useState(false);

  const toggle = useKnowledgeToggle(() => setHasChanges(true));
  const remove = useMutation(
    (itemId: string) =>
      api.DELETE("/v1/businesses/{business_id}/knowledge/{item_id}", {
        params: { path: { business_id: business.id, item_id: itemId } },
      }),
    { stale: [queryKeys.knowledge.all(business.id), queryKeys.profile.all(business.id), queryKeys.assistant.all(business.id)] },
  );

  const all = items.items ?? [];
  const isFiltered = filter.kind !== "all" || filter.status !== "all";
  const groups = groupByKind(sortByTitle(all, locale), kinds);
  const openQuestions = (questions.data?.items ?? []).filter((question) => !question.is_resolved).length;
  const hasMoreQuestions = Boolean(questions.data?.next_cursor);

  // A saved item stays in each list only while it matches the list's filters.
  const replaceItem = (saved: KnowledgeItemDetails) => toggle.saveIntoLists(saved);

  const openEditor = (target: KnowledgeEditorTarget) => setEditor((current) => ({ key: (current?.key ?? 0) + 1, target }));

  /** Open a search result in the editor. */
  const openById = (id: string) => {
    const item = all.find((entry) => entry.id === id);
    if (item) {
      openEditor({ mode: "edit", id: item.id, item });
      return;
    }
    // Not loaded yet (on a later page or filtered out): fetch it first.
    unwrap(
      api.GET("/v1/businesses/{business_id}/knowledge/{item_id}", {
        params: { path: { business_id: business.id, item_id: id }, query: { language: locale } },
      }),
    ).then(
      (found) => openEditor({ mode: "edit", id: found.id, item: found }),
      (error: unknown) => toast.error(error),
    );
  };

  const confirmDelete = async () => {
    if (!deleting) {
      return;
    }
    const result = await remove.run(deleting.id);
    if (result.ok) {
      const deletedId = deleting.id;
      items.updateItems((list) => list.filter((item) => item.id !== deletedId));
      toast.success(t("knowledge.items.deleted", { title: deleting.title }));
      setHasChanges(true);
      setDeleting(null);
    }
  };

  const onSaved = (saved: KnowledgeItemDetails) => {
    replaceItem(saved);
    setHasChanges(true);
    setEditor(null);
  };

  return {
    kinds,
    filter,
    setFilter,
    items,
    isFiltered,
    groups,
    openQuestions,
    hasMoreQuestions,
    expanded,
    expand: (kind: KnowledgeItemKind) => setExpanded((current) => new Set(current).add(kind)),
    editor,
    openEditor,
    closeEditor: () => setEditor(null),
    onSaved,
    openById,
    deleting,
    setDeleting,
    isDeleting: remove.isPending,
    confirmDelete,
    setActive: toggle.setActive,
    hasChanges,
    defaultKind: filter.kind !== "all" ? filter.kind : (kinds[0] ?? "service"),
  };
}

export type KnowledgeItemsState = ReturnType<typeof useKnowledgeItems>;
