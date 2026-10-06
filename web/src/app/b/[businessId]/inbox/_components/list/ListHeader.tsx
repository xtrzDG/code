"use client";

/**
 * The bar at the top of the conversation list. With nothing selected: a box
 * that selects every conversation with something to resolve, the row
 * density (Comfortable or Compact, remembered for the person) and, on
 * large screens, the keyboard shortcuts. With a selection: how many,
 * "Mark resolved" and "Clear selection".
 */

import { useEffect, useId, useRef } from "react";

import { IconCheck } from "@/components/icons";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { INBOX_DENSITIES, type InboxDensity } from "../../_lib/inboxLayout";

function DensityGlyph({ density }: { density: InboxDensity }) {
  const rows = density === "compact" ? [5, 10, 15, 20] : [6, 16];
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeLinecap="round" className="size-4" aria-hidden>
      {rows.map((y) => (
        <path key={y} d={`M4 ${y}h16`} strokeWidth={density === "compact" ? 1.75 : 4} />
      ))}
    </svg>
  );
}

function KeyboardGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" className="size-4" aria-hidden>
      <rect x="3" y="6" width="18" height="12" rx="2" />
      <path d="M7 10h.01M11 10h.01M15 10h.01M7 14h10" />
    </svg>
  );
}

function DensityToggle({ value, onChange }: { value: InboxDensity; onChange: (density: InboxDensity) => void }) {
  const { t } = useI18n();
  const name = useId();
  return (
    <fieldset className="shrink-0">
      <legend className="sr-only">{t("inboxTriage.density.label")}</legend>
      <div className="flex rounded-lg border border-line bg-surface-muted p-0.5">
        {INBOX_DENSITIES.map((density) => (
          <label
            key={density}
            title={t(`inboxTriage.density.${density}`)}
            className={cn(
              "flex h-7 cursor-pointer items-center gap-1.5 rounded-md px-2 text-xs font-medium whitespace-nowrap transition-colors",
              "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-focus",
              value === density ? "bg-surface text-ink ring-1 ring-line-strong/40" : "text-ink-subtle hover:text-ink",
            )}
          >
            <input
              type="radio"
              name={name}
              value={density}
              checked={value === density}
              onChange={() => onChange(density)}
              className="sr-only"
            />
            <DensityGlyph density={density} />
            <span className="sr-only @sm/list:not-sr-only">{t(`inboxTriage.density.${density}`)}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** A box for every selectable row: checked, partly (some) or empty. */
function SelectAllBox({ state, onToggle }: { state: "all" | "some" | "none"; onToggle: () => void }) {
  const { t } = useI18n();
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (input.current) {
      input.current.indeterminate = state === "some";
    }
  }, [state]);
  return (
    <label className="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-md hover:bg-surface-muted">
      <input
        ref={input}
        type="checkbox"
        checked={state === "all"}
        onChange={onToggle}
        aria-label={t("inboxTriage.select.all")}
        className="peer sr-only"
      />
      <span
        aria-hidden
        className={cn(
          "flex size-[1.125rem] items-center justify-center rounded-[0.3rem] border transition-colors peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus",
          state === "none" ? "border-line-strong bg-surface" : "border-accent-solid bg-accent-solid text-on-accent",
        )}
      >
        {state === "all" ? <IconCheck className="size-3.5" /> : state === "some" ? <span className="h-0.5 w-2 rounded bg-current" /> : null}
      </span>
    </label>
  );
}

export function ListHeader({
  density,
  onDensity,
  selection,
  selectedCount,
  canSelect,
  isResolving,
  onToggleAll,
  onResolve,
  onClear,
  onShortcuts,
}: {
  density: InboxDensity;
  onDensity: (density: InboxDensity) => void;
  selection: "all" | "some" | "none";
  selectedCount: number;
  /** Some row of the list has something to resolve. */
  canSelect: boolean;
  isResolving: boolean;
  onToggleAll: () => void;
  onResolve: () => void;
  onClear: () => void;
  onShortcuts: () => void;
}) {
  const { t, tp } = useI18n();
  const isSelecting = selectedCount > 0;
  return (
    <div
      className={cn(
        "sticky top-0 z-20 flex min-h-11 items-center gap-1.5 border-b border-line px-2 py-1.5 transition-colors",
        isSelecting ? "bg-accent-soft" : "bg-surface",
      )}
    >
      {canSelect ? <SelectAllBox state={selection} onToggle={onToggleAll} /> : null}
      {isSelecting ? (
        <>
          <p className="min-w-0 flex-1 truncate text-sm font-medium text-ink" aria-live="polite">
            {tp("inboxTriage.select.count", selectedCount)}
          </p>
          <Button size="sm" onClick={onResolve} isLoading={isResolving} className="shrink-0">
            {t("inboxTriage.select.resolve")}
          </Button>
          <Button size="sm" variant="ghost" onClick={onClear} className="shrink-0">
            {t("inboxTriage.select.clear")}
          </Button>
        </>
      ) : (
        <>
          <span className="flex-1" />
          <DensityToggle value={density} onChange={onDensity} />
          <Button
            size="sm"
            variant="ghost"
            onClick={onShortcuts}
            aria-label={t("inboxTriage.keys.open")}
            title={t("inboxTriage.keys.open")}
            aria-keyshortcuts="Shift+?"
            className="w-8 shrink-0 px-0 max-lg:hidden"
          >
            <KeyboardGlyph />
          </Button>
        </>
      )}
    </div>
  );
}
