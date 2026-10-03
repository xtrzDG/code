"use client";

/**
 * Search and filters above the list. The search looks through every
 * conversation (it moves the list to "All"); the filters sit under it on
 * large screens and fold into a sheet on phones, behind one button that
 * says how many are set.
 */

import { useEffect, useId, useRef, useState } from "react";

import { IconSearch, IconX } from "@/components/icons";
import { Button, Input, Sheet } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { clearedFilters, sheetFilterCount, withSearch, type InboxFilters } from "../../_lib/inboxModel";
import { InboxFilterFields } from "./InboxFilterFields";

const SEARCH_DELAY_MS = 300;

function FilterGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" className="size-4" aria-hidden>
      <path d="M4 7h16M7 12h10M10 17h4" />
    </svg>
  );
}

export function InboxToolbar({ filters, onChange }: { filters: InboxFilters; onChange: (filters: InboxFilters) => void }) {
  const { t } = useI18n();
  const id = useId();
  // Typed text not yet applied; null shows the applied search.
  const [draft, setDraft] = useState<string | null>(null);
  const [isSheetOpen, setSheetOpen] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const filterCount = sheetFilterCount(filters);
  const search = draft ?? filters.search;

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const typeSearch = (text: string) => {
    setDraft(text);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      onChange(withSearch(filters, text));
      setDraft(null);
    }, SEARCH_DELAY_MS);
  };

  const clearSearch = () => {
    window.clearTimeout(timer.current);
    setDraft(null);
    onChange(withSearch(filters, ""));
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="relative min-w-0 flex-1">
          <label htmlFor={`${id}-search`} className="sr-only">
            {t("inbox.searchLabel")}
          </label>
          <IconSearch className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden />
          <Input
            id={`${id}-search`}
            type="search"
            value={search}
            onChange={(event) => typeSearch(event.target.value)}
            placeholder={t("inbox.searchPlaceholder")}
            autoComplete="off"
            enterKeyHint="search"
            className="h-10 px-9 [&::-webkit-search-cancel-button]:hidden"
          />
          {search ? (
            <button
              type="button"
              onClick={clearSearch}
              aria-label={t("inbox.clearSearch")}
              className="absolute end-1 top-1/2 flex size-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-md text-ink-subtle hover:bg-surface-muted hover:text-ink"
            >
              <IconX className="size-4" aria-hidden />
            </button>
          ) : null}
        </div>
        <Button
          variant="secondary"
          className="h-10 lg:hidden"
          leadingIcon={<FilterGlyph />}
          aria-haspopup="dialog"
          aria-expanded={isSheetOpen}
          onClick={() => setSheetOpen(true)}
        >
          {filterCount > 0 ? t("inbox.filters.openWithCount", { count: filterCount }) : t("inbox.filters.open")}
        </Button>
      </div>

      <div className="hidden lg:block">
        <InboxFilterFields filters={filters} onChange={onChange} layout="inline" />
      </div>

      <Sheet
        open={isSheetOpen}
        onClose={() => setSheetOpen(false)}
        title={t("inbox.filters.title")}
        description={filters.view === "all" ? t("inbox.filters.description") : undefined}
        footer={
          <>
            {filterCount > 0 ? (
              <Button variant="ghost" onClick={() => onChange(clearedFilters(filters))}>
                {t("inbox.filters.clear")}
              </Button>
            ) : null}
            <Button onClick={() => setSheetOpen(false)}>{t("inbox.filters.show")}</Button>
          </>
        }
      >
        <InboxFilterFields filters={filters} onChange={onChange} layout="sheet" />
      </Sheet>
    </div>
  );
}
