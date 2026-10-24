"use client";

/**
 * A page's filters: in a row on large screens, and on phones folded behind
 * one "Filters" button whose chip says how many are set, opening a bottom
 * sheet with the same fields, "Clear filters" and "Show". Filters apply as
 * they change (the list behind the sheet follows), so "Show" only closes.
 *
 *     <FilterSheet activeCount={count} onClear={reset} inline={<Fields layout="row" />}>
 *       <Fields layout="sheet" />
 *     </FilterSheet>
 *
 * `trailing` sits beside the phone's button (a secondary page action).
 */

import { useState, type ReactNode } from "react";

import { useI18n } from "@/i18n/client";

import { Button } from "./Button";
import { Sheet } from "./Sheet";

function FilterGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" className="size-4" aria-hidden>
      <path d="M4 7h16M7 12h10M10 17h4" />
    </svg>
  );
}

export function FilterSheet({
  activeCount,
  onClear,
  inline,
  trailing,
  description,
  showLabel,
  className,
  children,
}: {
  /** How many filters differ from their defaults. */
  activeCount: number;
  /** Puts every filter back to its default. */
  onClear: () => void;
  /** The fields for large screens. */
  inline: ReactNode;
  /** Beside the phone's Filters button. */
  trailing?: ReactNode;
  description?: ReactNode;
  /** The sheet's closing button ("Show bookings"); "Show" by default. */
  showLabel?: string;
  className?: string;
  /** The fields for the sheet. */
  children: ReactNode;
}) {
  const { t } = useI18n();
  const [isOpen, setOpen] = useState(false);

  return (
    <div className={className}>
      <div className="flex flex-wrap items-center gap-2 lg:hidden">
        <Button
          variant="secondary"
          className="h-10"
          leadingIcon={<FilterGlyph />}
          aria-haspopup="dialog"
          aria-expanded={isOpen}
          aria-label={activeCount > 0 ? t("chrome.filters.openWithCount", { count: activeCount }) : undefined}
          onClick={() => setOpen(true)}
        >
          {t("chrome.filters.open")}
          {activeCount > 0 ? (
            <span
              aria-hidden
              className="ms-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-accent-solid px-1.5 text-xs font-semibold text-on-accent tabular-nums"
            >
              {activeCount}
            </span>
          ) : null}
        </Button>
        {trailing}
      </div>

      <div className="hidden lg:block">{inline}</div>

      <Sheet
        open={isOpen}
        onClose={() => setOpen(false)}
        title={t("chrome.filters.title")}
        description={description}
        footer={
          <>
            {activeCount > 0 ? (
              <Button variant="ghost" onClick={onClear}>
                {t("chrome.filters.clear")}
              </Button>
            ) : null}
            <Button onClick={() => setOpen(false)}>{showLabel ?? t("chrome.filters.show")}</Button>
          </>
        }
      >
        {children}
      </Sheet>
    </div>
  );
}
