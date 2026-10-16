"use client";

import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { KnowledgeItemsState } from "../../_lib/useKnowledgeItems";
import { KIND_GROUP_LABELS } from "../hooks";
import { KnowledgeItemRow } from "./KnowledgeItemRow";

const GROUP_PAGE_SIZE = 20;

/** The loaded items by kind (the first ones of a long group, then "show all") and "show more". */
export function KnowledgeGroups({ list }: { list: KnowledgeItemsState }) {
  const { t } = useI18n();
  const { items, groups, expanded } = list;
  return (
    <div className="divide-y divide-line">
      {groups.map((group) => {
        const isExpanded = expanded.has(group.kind);
        const shown = isExpanded ? group.items : group.items.slice(0, GROUP_PAGE_SIZE);
        const headingId = `knowledge-group-${group.kind}`;
        return (
          <section key={group.kind} aria-labelledby={headingId}>
            <h2 id={headingId} className="bg-surface-muted/60 px-4 py-2 text-xs font-semibold tracking-wide text-ink-muted uppercase sm:px-6">
              {t(KIND_GROUP_LABELS[group.kind])}
              {items.hasMore ? null : <span className="font-normal"> · {group.items.length}</span>}
            </h2>
            <ul className="divide-y divide-line">
              {shown.map((item) => (
                <KnowledgeItemRow
                  key={item.id}
                  item={item}
                  resources={list.resources}
                  onToggle={(isActive) => void list.setActive(item, isActive)}
                  onEdit={() => list.openEditor({ mode: "edit", id: item.id, item })}
                  onDelete={() => list.setDeleting(item)}
                />
              ))}
            </ul>
            {group.items.length > shown.length ? (
              <div className="px-4 py-3 sm:px-6">
                <Button variant="ghost" size="sm" onClick={() => list.expand(group.kind)}>
                  {items.hasMore
                    ? t("knowledge.items.showRest", { count: group.items.length - shown.length })
                    : t("knowledge.items.showAll", { count: group.items.length })}
                </Button>
              </div>
            ) : null}
          </section>
        );
      })}
      {items.hasMore || items.moreError ? (
        <div className="flex flex-col items-center gap-2 px-4 py-4 text-center sm:px-6">
          {items.moreError ? (
            <p className="text-sm text-danger" role="alert">
              {t("knowledge.paging.failed")}
            </p>
          ) : null}
          <Button variant="secondary" isLoading={items.isLoadingMore} loadingText={t("common.loading")} onClick={items.loadMore}>
            {items.moreError ? t("common.retry") : t("knowledge.paging.more")}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
