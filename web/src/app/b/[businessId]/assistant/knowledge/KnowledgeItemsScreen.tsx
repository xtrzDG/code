"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { StillIndexingNote } from "@/components/lists/StillIndexingNote";
import { IconBook, IconPlus } from "@/components/icons";
import { Alert, Button, ButtonLink, Card, ConfirmDialog, EmptyState, ErrorState, LoadingRegion, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import { KnowledgeGroups } from "./_components/items/KnowledgeGroups";
import { KnowledgeSearch } from "./_components/items/KnowledgeSearch";
import { KnowledgeToolbar } from "./_components/items/KnowledgeToolbar";
import { KnowledgeItemEditor } from "./_components/KnowledgeItemEditor";
import { KnowledgeRowsSkeleton } from "./_components/KnowledgeSkeleton";
import { useKnowledgeItems } from "./_lib/useKnowledgeItems";

/**
 * Knowledge -> Items: everything the assistant knows, by kind, with search
 * and editing. The list is paged and filtered by the API; loaded items are
 * grouped by kind and sorted by title.
 */
export function KnowledgeItemsScreen() {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const list = useKnowledgeItems();
  const { items, kinds, openQuestions, editor, deleting } = list;
  const base = businessPath(business.id, "assistant/knowledge");
  const all = items.items ?? [];

  // On phones the items come first; trying the search waits below them.
  return (
    <div className="flex flex-col gap-6">
      {openQuestions > 0 ? (
        <Alert
          tone="warning"
          title={
            list.hasMoreQuestions
              ? t("knowledge.items.questionsAlertMany", { count: openQuestions })
              : tp("knowledge.items.questionsAlert", openQuestions)
          }
          action={
            <ButtonLink href={`${base}/questions`} size="sm" variant="secondary">
              {t("knowledge.items.questionsAction")}
            </ButtonLink>
          }
        >
          {t("knowledge.items.questionsHint")}
        </Alert>
      ) : null}

      <StillIndexingNote isIndexing={items.page?.is_indexing} />

      <div className="max-lg:order-last">
        <KnowledgeSearch onOpen={list.openById} />
      </div>

      <Card padded={false}>
        <KnowledgeToolbar list={list} />

        {items.isLoading ? (
          <LoadingRegion label={t("common.loading")}>
            <KnowledgeRowsSkeleton />
          </LoadingRegion>
        ) : items.error ? (
          <ErrorState error={items.error} onRetry={items.reload} />
        ) : all.length === 0 && !list.isFiltered ? (
          <EmptyState
            icon={<IconBook className="size-6" />}
            title={t("knowledge.items.emptyTitle")}
            description={t("knowledge.items.emptyDescription")}
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => list.openEditor({ mode: "create", kind: list.defaultKind })}>
                  {t("knowledge.items.add")}
                </Button>
                <ButtonLink href={`${base}/import`} variant="secondary">
                  {t("knowledge.items.import")}
                </ButtonLink>
              </div>
            }
          />
        ) : all.length === 0 ? (
          <EmptyState
            title={t("knowledge.items.noMatchesTitle")}
            description={t("knowledge.items.noMatchesDescription")}
            action={
              <Button variant="secondary" onClick={() => list.setFilter({ kind: "all", status: "all" })}>
                {t("knowledge.items.resetFilters")}
              </Button>
            }
          />
        ) : (
          <div className={items.isPlaceholder ? "animate-settle opacity-60 transition-opacity" : "animate-settle transition-opacity"} aria-busy={items.isPlaceholder || undefined}>
            <KnowledgeGroups list={list} />
          </div>
        )}
      </Card>

      {editor ? (
        <KnowledgeItemEditor key={editor.key} target={editor.target} kinds={kinds} onClose={list.closeEditor} onSaved={list.onSaved} />
      ) : null}

      <ConfirmDialog
        open={deleting !== null}
        title={t("knowledge.items.deleteTitle")}
        description={deleting ? <UserSentence text={t("knowledge.items.deleteDescription")} values={{ title: deleting.title }} /> : undefined}
        confirmLabel={t("common.delete")}
        isPending={list.isDeleting}
        onConfirm={() => void list.confirmDelete()}
        onClose={() => list.setDeleting(null)}
      />
    </div>
  );
}
