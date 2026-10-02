"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { unwrap } from "@/api/result";
import type { KnowledgeItemDetails, KnowledgeItemKind } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { usePagedList } from "@/components/content/usePagedList";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import {
  filterKnowledgeItems,
  groupByKind,
  sortByTitle,
  type KnowledgeFilter,
  type KnowledgeStatusFilter,
} from "@/lib/knowledge/kinds";

import { useKnowledgeKinds } from "../_components/hooks";
import type { KnowledgeEditorTarget } from "../_components/KnowledgeItemEditor";

/** Items per request; "show more" loads the next page (newest first). */
const ITEMS_PAGE_SIZE = 100;
/** Open questions counted for the warning; more are shown as "more than". */
const QUESTIONS_ALERT_LIMIT = 100;

function statusQuery(status: KnowledgeStatusFilter): "true" | "false" | undefined {
  return status === "all" ? undefined : status === "active" ? "true" : "false";
}

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
  const items = usePagedList(
    (cursor) =>
      api.GET("/v1/businesses/{business_id}/knowledge", {
        params: {
          path: { business_id: business.id },
          query: {
            language: locale,
            kind: filter.kind === "all" ? undefined : filter.kind,
            is_active: statusQuery(filter.status),
            limit: String(ITEMS_PAGE_SIZE),
            cursor: cursor ?? undefined,
          },
        },
      }),
    [business.id, locale, filter.kind, filter.status],
  );
  const questions = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/unanswered-questions", {
        params: { path: { business_id: business.id }, query: { limit: String(QUESTIONS_ALERT_LIMIT) } },
      }),
    [business.id],
  );

  const [expanded, setExpanded] = useState<ReadonlySet<KnowledgeItemKind>>(new Set());
  const [editor, setEditor] = useState<{ key: number; target: KnowledgeEditorTarget } | null>(null);
  const [deleting, setDeleting] = useState<KnowledgeItemDetails | null>(null);
  const [toggling, setToggling] = useState<ReadonlySet<string>>(new Set());
  const [hasChanges, setHasChanges] = useState(false);

  const toggle = useApiMutation((itemId: string, isActive: boolean) =>
    api.PATCH("/v1/businesses/{business_id}/knowledge/{item_id}", {
      params: { path: { business_id: business.id, item_id: itemId }, query: { language: locale } },
      body: { is_active: isActive },
    }),
  );
  const remove = useApiMutation((itemId: string) =>
    api.DELETE("/v1/businesses/{business_id}/knowledge/{item_id}", {
      params: { path: { business_id: business.id, item_id: itemId } },
    }),
  );

  const all = items.items;
  const isFiltered = filter.kind !== "all" || filter.status !== "all";
  const groups = groupByKind(sortByTitle(all, locale), kinds);
  const openQuestions = (questions.data?.items ?? []).filter((question) => !question.is_resolved).length;
  const hasMoreQuestions = Boolean(questions.data?.next_cursor);

  // A saved item stays in the list only while it matches the filters.
  const replaceItem = (saved: KnowledgeItemDetails) =>
    items.update((list) => {
      const others = list.filter((item) => item.id !== saved.id);
      if (filterKnowledgeItems([saved], filter).length === 0) {
        return others;
      }
      const exists = others.length < list.length;
      return exists ? list.map((item) => (item.id === saved.id ? saved : item)) : [saved, ...list];
    });

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

  const setActive = async (item: KnowledgeItemDetails, isActive: boolean) => {
    setToggling((current) => new Set(current).add(item.id));
    const result = await toggle.run(item.id, isActive);
    setToggling((current) => {
      const next = new Set(current);
      next.delete(item.id);
      return next;
    });
    if (result.ok) {
      replaceItem(result.data);
      setHasChanges(true);
      toast.success(isActive ? t("knowledge.items.switchedOn", { title: item.title }) : t("knowledge.items.switchedOff", { title: item.title }));
    }
  };

  const confirmDelete = async () => {
    if (!deleting) {
      return;
    }
    const result = await remove.run(deleting.id);
    if (result.ok) {
      const deletedId = deleting.id;
      items.update((list) => list.filter((item) => item.id !== deletedId));
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
    toggling,
    setActive,
    hasChanges,
    defaultKind: filter.kind !== "all" ? filter.kind : (kinds[0] ?? "service"),
  };
}

export type KnowledgeItemsState = ReturnType<typeof useKnowledgeItems>;
