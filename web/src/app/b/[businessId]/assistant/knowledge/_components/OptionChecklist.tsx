"use client";

import { useId, useState, type ReactNode } from "react";

import { Badge, Checkbox, Fieldset, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";

export interface ChecklistOption {
  id: string;
  label: string;
  /** A second line: the kind, duration and price, say. */
  note?: string;
  /** Switched off: still listed (and kept when ticked), marked "off". */
  isOff?: boolean;
}

/** Above this many options a name filter appears. */
const FILTER_FROM = 9;

/**
 * A multi-select as a fieldset of checkboxes (who performs a service, the
 * services of a master): every option one tap, a name filter for long
 * lists, the ticked count announced. `empty` shows when there is nothing
 * to choose from.
 */
export function OptionChecklist({
  legend,
  hint,
  options,
  selected,
  onChange,
  empty,
  error,
}: {
  legend: string;
  hint?: ReactNode;
  options: readonly ChecklistOption[];
  selected: readonly string[];
  onChange: (ids: string[]) => void;
  empty?: ReactNode;
  error?: string;
}) {
  const { t, tp } = useI18n();
  const idPrefix = useId();
  const [query, setQuery] = useState("");
  const needle = query.trim().toLocaleLowerCase();
  const shown = needle ? options.filter((option) => option.label.toLocaleLowerCase().includes(needle)) : options;
  const toggle = (id: string, checked: boolean) =>
    onChange(checked ? [...selected.filter((item) => item !== id), id] : selected.filter((item) => item !== id));

  return (
    <Fieldset
      legend={
        <span className="flex flex-wrap items-baseline gap-x-2">
          <span>{legend}</span>
          {selected.length > 0 ? (
            <span className="text-xs font-normal text-ink-muted" aria-live="polite">
              {tp("knowledge.offer.selectedCount", selected.length)}
            </span>
          ) : null}
        </span>
      }
      hint={hint}
      error={error}
    >
      {options.length === 0 ? (
        (empty ?? null)
      ) : (
        <>
          {options.length >= FILTER_FROM ? (
            <Input
              type="search"
              aria-label={t("knowledge.offer.filter")}
              placeholder={t("knowledge.offer.filter")}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="max-w-xs"
            />
          ) : null}
          {shown.length === 0 ? (
            <p className="text-sm text-ink-muted">{t("knowledge.offer.noMatches", { query: query.trim() })}</p>
          ) : (
            <div className="grid max-h-72 grid-cols-[repeat(auto-fill,minmax(12rem,1fr))] gap-2 overflow-y-auto p-0.5">
              {shown.map((option) => (
                <Checkbox
                  key={option.id}
                  id={`${idPrefix}-${option.id}`}
                  className="min-h-11 rounded-xl border border-line bg-surface px-3 py-2.5 transition-colors has-checked:border-accent/40 has-checked:bg-accent-soft"
                  label={
                    <span className="flex flex-wrap items-center gap-1.5">
                      <span dir="auto" data-user-content className="break-words">
                        {option.label}
                      </span>
                      {option.isOff ? <Badge>{t("knowledge.offer.resourceOff")}</Badge> : null}
                    </span>
                  }
                  description={option.note}
                  checked={selected.includes(option.id)}
                  onChange={(event) => toggle(option.id, event.target.checked)}
                />
              ))}
            </div>
          )}
        </>
      )}
    </Fieldset>
  );
}
