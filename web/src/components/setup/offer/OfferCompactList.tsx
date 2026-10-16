"use client";

/**
 * The offer on a phone once it is long (Assistant → Business profile):
 * every saved line is one short row (name, price, minutes) that opens into
 * the full line for editing, one at a time, with "Done" under it; lines of
 * different kinds sit in groups folded to their name and count; a search
 * shows the lines whose name holds what was typed. A line that is new, not
 * saved yet or failed to save stays open, so nothing unsaved hides.
 */

import { useId, useState, type ClipboardEvent, type KeyboardEvent, type ReactNode } from "react";

import type { KnowledgeItemKind } from "@/api/types";
import { IconChevronDown, IconChevronRight, IconSearch } from "@/components/icons";
import { Badge, Button, Input, UserContent } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { groupByKind, matchesQuery, rowMinutes } from "@/lib/tunnel/offerCompact";
import type { TunnelOfferRow } from "@/lib/tunnel/offer";

import type { OfferRows } from "./useOfferRows";

/** Focuses, once drawn, the element of row `key` that `find` picks: the open line's name, or the folded row. */
function focusLater(key: string, find: (row: HTMLElement) => HTMLElement | null) {
  requestAnimationFrame(() => {
    const row = Array.from(document.querySelectorAll<HTMLElement>("[data-row-key]")).find((element) => element.dataset.rowKey === key);
    if (row) find(row)?.focus();
  });
}

const nameOf = (row: HTMLElement) => row.querySelector<HTMLElement>("input[data-offer-name]");
const foldOf = (row: HTMLElement) => row.querySelector<HTMLElement>("[data-offer-fold]");

export function OfferCompactList({
  table,
  currency,
  kinds,
  onPaste,
  renderLine,
}: {
  table: OfferRows;
  currency: string;
  /** The niche's kinds, the order of the groups. */
  kinds: readonly KnowledgeItemKind[];
  onPaste: (event: ClipboardEvent<HTMLUListElement>) => void;
  /** The full, editable line (OfferLine) with `footer` under it. */
  renderLine: (row: TunnelOfferRow, index: number, footer: ReactNode) => ReactNode;
}) {
  const { t, tp, locale } = useI18n();
  const searchId = useId();
  const [query, setQuery] = useState("");
  const [openKey, setOpenKey] = useState<string | null>(null);
  const [unfolded, setUnfolded] = useState<ReadonlySet<KnowledgeItemKind>>(new Set());

  const mustStayOpen = (row: TunnelOfferRow) => row.isSuggestion || row.id === null || row.title.trim() === "" || table.status[row.key] === "failed";
  const isOpen = (row: TunnelOfferRow) => row.key === openKey || mustStayOpen(row);
  const shown = table.rows.filter((row) => isOpen(row) || matchesQuery(row.title, query, locale));
  const isSearching = query.trim() !== "";
  // Lines of more than one kind are grouped by it.
  const showGroups = new Set(table.rows.map((row) => row.kind)).size > 1;
  const groups = showGroups ? groupByKind(shown, kinds) : [{ kind: null, rows: shown }];
  const indexOf = new Map(table.rows.map((row, index) => [row.key, index]));
  const isUnfolded = (kind: KnowledgeItemKind | null, rows: readonly TunnelOfferRow[]) =>
    kind === null || isSearching || unfolded.has(kind) || rows.some(isOpen);
  const visibleKeys = groups.flatMap((group) => (isUnfolded(group.kind, group.rows) ? group.rows.map((row) => row.key) : []));

  const open = (key: string) => {
    setOpenKey(key);
    focusLater(key, nameOf);
  };
  const done = (key: string) => {
    void table.save(key);
    setOpenKey(null);
    focusLater(key, foldOf);
  };
  const toggle = (kind: KnowledgeItemKind) =>
    setUnfolded((current) => {
      const next = new Set(current);
      if (!next.delete(kind)) next.add(kind);
      return next;
    });

  // Enter in an open line opens the next row shown (a new line after the last one).
  const onKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    const target = event.target as HTMLElement;
    if (event.key !== "Enter" || target.tagName !== "INPUT" || event.nativeEvent.isComposing) {
      return;
    }
    event.preventDefault();
    const key = target.closest<HTMLElement>("[data-row-key]")?.dataset.rowKey ?? "";
    const next = visibleKeys[visibleKeys.indexOf(key) + 1];
    if (next) {
      open(next);
    } else {
      table.add();
    }
  };

  const fold = (row: TunnelOfferRow) => {
    const minutes = rowMinutes(row);
    const price = row.price.trim() ? `${row.price.trim()} ${currency}` : t("profileEdit.offer.compact.noPrice");
    return (
      <li key={row.key} data-row-key={row.key}>
        <button
          type="button"
          data-offer-fold=""
          onClick={() => open(row.key)}
          className="flex min-h-12 w-full cursor-pointer items-center gap-3 rounded-2xl border border-line bg-surface/85 px-3.5 py-2.5 text-start transition-colors hover:border-line-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          <UserContent className="min-w-0 flex-1 truncate font-medium text-ink">{row.title}</UserContent>
          <span className={cn("shrink-0 text-sm tabular-nums", row.price.trim() ? "text-ink" : "text-ink-subtle")}>
            {price}
            {minutes === null ? null : <span className="text-ink-muted"> · {tp("profileEdit.offer.compact.minutes", minutes)}</span>}
          </span>
          <IconChevronRight className="size-4 shrink-0 text-ink-subtle rtl:-scale-x-100" aria-hidden />
        </button>
      </li>
    );
  };

  const line = (row: TunnelOfferRow) =>
    renderLine(
      row,
      indexOf.get(row.key) ?? 0,
      row.key === openKey && !mustStayOpen(row) ? (
        <div className="mt-2 flex justify-end">
          <Button size="sm" variant="secondary" onClick={() => done(row.key)}>
            {t("common.done")}
          </Button>
        </div>
      ) : null,
    );

  const list = (rows: readonly TunnelOfferRow[], label: string, id?: string) => (
    <ul id={id} aria-label={label} data-enter="own" onKeyDown={onKeyDown} onPaste={onPaste} className="space-y-2">
      {rows.map((row) => (isOpen(row) ? line(row) : fold(row)))}
    </ul>
  );

  return (
    <div className="space-y-3">
      <div className="relative">
        <IconSearch className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
        <Input
          type="search"
          dir="auto"
          aria-label={t("profileEdit.offer.compact.search")}
          placeholder={t("profileEdit.offer.compact.search")}
          value={query}
          maxLength={200}
          onChange={(event) => setQuery(event.target.value)}
          className="ps-9"
        />
      </div>
      {shown.length === 0 ? (
        <p role="status" className="px-1 text-sm text-ink-muted">
          {t("profileEdit.offer.compact.noMatches", { query: query.trim() })}
        </p>
      ) : null}
      {groups.map((group) => {
        if (group.kind === null) {
          return <div key="all">{list(group.rows, t("tunnelOffer.offer.tableLabel"))}</div>;
        }
        const kind = group.kind;
        const name = t(`knowledge.kindGroups.${kind}`);
        const isGroupOpen = isUnfolded(kind, group.rows);
        const listId = `${searchId}-${kind}`;
        return (
          <section key={kind} className="space-y-2">
            <button
              type="button"
              aria-expanded={isGroupOpen}
              aria-controls={isGroupOpen ? listId : undefined}
              aria-label={tp("profileEdit.offer.compact.group", group.rows.length, { kind: name })}
              disabled={isSearching}
              onClick={() => toggle(kind)}
              className="flex min-h-11 w-full cursor-pointer items-center gap-2 rounded-xl px-2 text-start text-sm font-semibold text-ink hover:bg-surface-muted disabled:cursor-default disabled:hover:bg-transparent"
            >
              <IconChevronDown className={cn("size-4 shrink-0 text-ink-subtle transition-transform", !isGroupOpen && "-rotate-90 rtl:rotate-90")} aria-hidden />
              <span className="min-w-0 flex-1 truncate">{name}</span>
              <Badge tone="neutral">{group.rows.length}</Badge>
            </button>
            {isGroupOpen ? list(group.rows, name, listId) : null}
          </section>
        );
      })}
    </div>
  );
}
