"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useApiMutation, useApiQuery } from "@/api/hooks";
import { unwrap } from "@/api/result";
import type { KnowledgeItemDetails, KnowledgeItemKind, Schema } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/content/ConfirmDialog";
import { IconPencil, IconSearch, IconUpload } from "@/components/content/icons";
import { Switch } from "@/components/content/Switch";
import { usePagedList } from "@/components/content/usePagedList";
import { IconBook, IconPlus, IconTrash, IconX } from "@/components/icons";
import {
  Alert,
  Badge,
  Button,
  ButtonLink,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingBlock,
  Select,
  Spinner,
  useToast,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import {
  filterKnowledgeItems,
  groupByKind,
  sortByTitle,
  type KnowledgeFilter,
  type KnowledgeStatusFilter,
} from "@/lib/knowledge/kinds";
import { businessPath } from "@/lib/navigation";

import { KIND_GROUP_LABELS, KIND_LABELS, useKnowledgeKinds } from "./_components/hooks";
import { KnowledgeItemEditor, type KnowledgeEditorTarget } from "./_components/KnowledgeItemEditor";
import { ReassemblyNotice } from "./_components/ReassemblyNotice";

type KnowledgeItemView = Schema<"KnowledgeItemView">;

const GROUP_PAGE_SIZE = 20;
const SEARCH_LIMIT = 10;
/** Items per request; "show more" loads the next page (newest first). */
const ITEMS_PAGE_SIZE = 100;
/** Open questions counted for the warning; more are shown as "more than". */
const QUESTIONS_ALERT_LIMIT = 100;

function statusQuery(status: KnowledgeStatusFilter): "true" | "false" | undefined {
  return status === "all" ? undefined : status === "active" ? "true" : "false";
}

/**
 * Knowledge -> Items: everything the assistant knows, by kind, with search
 * and editing. The list is paged and filtered by the API; loaded items are
 * grouped by kind and sorted by title.
 */
export function KnowledgeItemsScreen() {
  const { t, tp, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const kinds = useKnowledgeKinds();
  const base = businessPath(business.id, "knowledge");

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

  const defaultKind = filter.kind !== "all" ? filter.kind : (kinds[0] ?? "service");

  return (
    <div className="space-y-6">
      {openQuestions > 0 ? (
        <Alert
          tone="warning"
          title={
            hasMoreQuestions
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
      {hasChanges ? <ReassemblyNotice /> : null}

      <KnowledgeSearch
        onOpen={(id) => {
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
        }}
      />

      <Card padded={false}>
        <div className="flex flex-col gap-3 border-b border-line px-4 py-4 sm:flex-row sm:items-end sm:justify-between sm:px-6">
          <div className="grid grid-cols-2 gap-3 sm:flex sm:flex-wrap">
            <Field label={t("knowledge.items.kindFilter")} className="sm:w-56">
              {(control) => (
                <Select
                  {...control}
                  value={filter.kind}
                  onChange={(event) => setFilter((current) => ({ ...current, kind: event.target.value as KnowledgeFilter["kind"] }))}
                >
                  <option value="all">{t("knowledge.items.allKinds")}</option>
                  {kinds.map((kind) => (
                    <option key={kind} value={kind}>
                      {t(KIND_GROUP_LABELS[kind])}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label={t("knowledge.items.statusFilter")} className="sm:w-56">
              {(control) => (
                <Select
                  {...control}
                  value={filter.status}
                  onChange={(event) => setFilter((current) => ({ ...current, status: event.target.value as KnowledgeStatusFilter }))}
                >
                  <option value="all">{t("knowledge.items.statusAll")}</option>
                  <option value="active">{t("knowledge.items.statusActive")}</option>
                  <option value="inactive">{t("knowledge.items.statusInactive")}</option>
                </Select>
              )}
            </Field>
          </div>
          <div className="flex flex-wrap gap-2">
            <ButtonLink href={`${base}/import`} variant="secondary" leadingIcon={<IconUpload className="size-4" aria-hidden />}>
              {t("knowledge.items.import")}
            </ButtonLink>
            <Button
              leadingIcon={<IconPlus className="size-4" aria-hidden />}
              onClick={() => openEditor({ mode: "create", kind: defaultKind })}
            >
              {t("knowledge.items.add")}
            </Button>
          </div>
        </div>

        {items.isLoading ? (
          <LoadingBlock label={t("common.loading")} />
        ) : items.error ? (
          <ErrorState error={items.error} onRetry={items.reload} />
        ) : all.length === 0 && !isFiltered ? (
          <EmptyState
            icon={<IconBook className="size-6" />}
            title={t("knowledge.items.emptyTitle")}
            description={t("knowledge.items.emptyDescription")}
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Button leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => openEditor({ mode: "create", kind: defaultKind })}>
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
              <Button variant="secondary" onClick={() => setFilter({ kind: "all", status: "all" })}>
                {t("knowledge.items.resetFilters")}
              </Button>
            }
          />
        ) : (
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
                        isToggling={toggling.has(item.id)}
                        onToggle={(isActive) => void setActive(item, isActive)}
                        onEdit={() => openEditor({ mode: "edit", id: item.id, item })}
                        onDelete={() => setDeleting(item)}
                      />
                    ))}
                  </ul>
                  {group.items.length > shown.length ? (
                    <div className="px-4 py-3 sm:px-6">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setExpanded((current) => new Set(current).add(group.kind))}
                      >
                        {items.hasMore
                          ? t("knowledge.items.showRest", { count: group.items.length - shown.length })
                          : t("knowledge.items.showAll", { count: group.items.length })}
                      </Button>
                    </div>
                  ) : null}
                </section>
              );
            })}
            {items.hasMore || items.loadMoreError ? (
              <div className="flex flex-col items-center gap-2 px-4 py-4 text-center sm:px-6">
                {items.loadMoreError ? (
                  <p className="text-sm text-danger" role="alert">
                    {t("knowledge.paging.failed")}
                  </p>
                ) : null}
                <Button variant="secondary" isLoading={items.isLoadingMore} loadingText={t("common.loading")} onClick={items.loadMore}>
                  {items.loadMoreError ? t("common.retry") : t("knowledge.paging.more")}
                </Button>
              </div>
            ) : null}
          </div>
        )}
      </Card>

      {editor ? (
        <KnowledgeItemEditor
          key={editor.key}
          target={editor.target}
          kinds={kinds}
          onClose={() => setEditor(null)}
          onSaved={(saved) => {
            replaceItem(saved);
            setHasChanges(true);
            setEditor(null);
          }}
        />
      ) : null}

      <ConfirmDialog
        open={deleting !== null}
        title={t("knowledge.items.deleteTitle")}
        description={deleting ? t("knowledge.items.deleteDescription", { title: deleting.title }) : undefined}
        confirmLabel={t("common.delete")}
        isPending={remove.isPending}
        onConfirm={() => void confirmDelete()}
        onClose={() => setDeleting(null)}
      />
    </div>
  );
}

function KnowledgeItemRow({
  item,
  isToggling,
  onToggle,
  onEdit,
  onDelete,
}: {
  item: KnowledgeItemDetails;
  isToggling: boolean;
  onToggle: (isActive: boolean) => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const meta = [
    item.price_minor !== null && item.price_minor !== undefined ? format.money(item.price_minor) : null,
    item.duration_minutes ? t("knowledge.items.minutes", { count: item.duration_minutes }) : null,
    (item.languages ?? []).length > 0 ? (item.languages ?? []).map((language) => languageName(language, locale)).join(", ") : null,
  ].filter((part): part is string => part !== null);

  return (
    <li className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:gap-6 sm:px-6">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium break-words text-ink" dir="auto">
            {item.title}
          </p>
          {!item.is_active ? (
            <Badge tone={item.source === "menu_import" ? "warning" : "neutral"}>
              {item.source === "menu_import" ? t("knowledge.items.importDraft") : t("knowledge.items.off")}
            </Badge>
          ) : null}
          {item.source === "unanswered_question" ? <Badge tone="info">{t("knowledge.items.fromQuestion")}</Badge> : null}
        </div>
        {item.body ? (
          <p className="mt-1 line-clamp-2 text-sm break-words whitespace-pre-line text-ink-muted" dir="auto">
            {item.body}
          </p>
        ) : null}
        {meta.length > 0 ? <p className="mt-1.5 text-sm text-ink-subtle">{meta.join(" · ")}</p> : null}
      </div>
      <div className="flex shrink-0 items-center gap-1 sm:pt-0.5">
        <span className="mr-2 flex items-center gap-2 text-sm text-ink-muted">
          {isToggling ? <Spinner size="sm" /> : null}
          <Switch
            checked={item.is_active}
            disabled={isToggling}
            label={t("knowledge.items.useToggle", { title: item.title })}
            onChange={onToggle}
          />
          <span aria-hidden className="sm:hidden">
            {item.is_active ? t("knowledge.items.used") : t("knowledge.items.notUsed")}
          </span>
        </span>
        <Button
          variant="ghost"
          size="sm"
          leadingIcon={<IconPencil className="size-4" aria-hidden />}
          aria-label={`${t("common.edit")}: ${item.title}`}
          onClick={onEdit}
        >
          {t("common.edit")}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          aria-label={`${t("common.delete")}: ${item.title}`}
          title={t("common.delete")}
          className="hover:text-danger"
          onClick={onDelete}
        >
          <IconTrash className="size-4" aria-hidden />
        </Button>
      </div>
    </li>
  );
}

/**
 * "What does the assistant find for this question?": the same search its
 * search_knowledge tool runs, in a customer language.
 */
function KnowledgeSearch({ onOpen }: { onOpen: (itemId: string) => void }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const [query, setQuery] = useState("");
  const [language, setLanguage] = useState(business.default_language);
  const [searched, setSearched] = useState<{ query: string; items: KnowledgeItemView[] } | null>(null);

  const search = useApiMutation((text: string, searchLanguage: string) =>
    api.POST("/v1/businesses/{business_id}/knowledge/search", {
      params: { path: { business_id: business.id } },
      body: { query: text, language: searchLanguage, limit: SEARCH_LIMIT },
    }),
  );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const text = query.trim();
    if (text === "") {
      setSearched(null);
      return;
    }
    const result = await search.run(text, language);
    if (result.ok) {
      setSearched({ query: text, items: result.data.items ?? [] });
    }
  };

  return (
    <Card title={t("knowledge.search.title")} description={t("knowledge.search.description")}>
      <form onSubmit={(event) => void submit(event)} className="flex flex-col gap-3 sm:flex-row sm:items-end" role="search">
        <Field label={t("knowledge.search.query")} className="min-w-0 flex-1">
          {(control) => (
            <Input
              {...control}
              type="search"
              dir="auto"
              value={query}
              maxLength={500}
              placeholder={t("knowledge.search.placeholder")}
              onChange={(event) => setQuery(event.target.value)}
            />
          )}
        </Field>
        <div className="flex items-end gap-3">
          {business.languages.length > 1 ? (
            <Field label={t("knowledge.search.language")} className="min-w-0 flex-1 sm:w-48 sm:flex-none">
              {(control) => (
                <Select {...control} value={language} onChange={(event) => setLanguage(event.target.value)}>
                  {business.languages.map((tag) => (
                    <option key={tag} value={tag}>
                      {languageName(tag, locale)}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          ) : null}
          <Button type="submit" variant="secondary" isLoading={search.isPending} leadingIcon={<IconSearch className="size-4" aria-hidden />}>
            {t("common.search")}
          </Button>
        </div>
      </form>

      {searched ? (
        <div className="mt-5 space-y-3" aria-live="polite">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium text-ink">
              {searched.items.length > 0
                ? t("knowledge.search.resultsFor", { query: searched.query })
                : t("knowledge.search.nothingFor", { query: searched.query })}
            </p>
            <Button variant="ghost" size="sm" leadingIcon={<IconX className="size-4" aria-hidden />} onClick={() => setSearched(null)}>
              {t("knowledge.search.clear")}
            </Button>
          </div>
          {searched.items.length === 0 ? (
            <p className="text-sm text-ink-muted">{t("knowledge.search.nothingHint")}</p>
          ) : (
            <ol className="divide-y divide-line rounded-xl border border-line">
              {searched.items.map((item, index) => (
                <li key={item.id} className="flex items-start gap-3 px-4 py-3">
                  <span className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-full bg-accent-soft text-xs font-semibold text-accent-ink">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium break-words text-ink" dir="auto">
                      {item.title}
                    </p>
                    <p className="text-sm text-ink-subtle">
                      {[t(KIND_LABELS[item.kind]), item.price_minor !== null && item.price_minor !== undefined ? format.money(item.price_minor) : null]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <Button variant="ghost" size="sm" aria-label={`${t("common.edit")}: ${item.title}`} onClick={() => onOpen(item.id)}>
                    <IconPencil className="size-4" aria-hidden />
                  </Button>
                </li>
              ))}
            </ol>
          )}
        </div>
      ) : null}
    </Card>
  );
}
