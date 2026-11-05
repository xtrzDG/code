"use client";

/**
 * Suggestions the owner takes one by one: dashed chips with a plus, each
 * named for what it adds ("Add “A complaint”"). Nothing is saved until a
 * chip is pressed.
 */

import type { ReactNode } from "react";

import { IconPlus } from "@/components/icons";

export interface Chip {
  key: string;
  text: string;
  /** The text is someone's own words (a question a customer asked): user content. */
  isUserContent?: boolean;
  /** What pressing it does, for screen readers and the tooltip. */
  label: string;
  onPick: () => void;
}

export function SuggestionChips({ title, chips, action }: { title: string; chips: readonly Chip[]; action?: ReactNode }) {
  if (chips.length === 0) {
    return null;
  }
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-medium tracking-wide text-ink-subtle uppercase">{title}</p>
        {action}
      </div>
      <ul className="flex flex-wrap gap-2">
        {chips.map((chip) => (
          <li key={chip.key} className="min-w-0 max-w-full">
            <button
              type="button"
              aria-label={chip.label}
              title={chip.label}
              onClick={chip.onPick}
              className="motion-press inline-flex max-w-full min-h-9 items-center gap-1.5 rounded-full border border-dashed border-line-strong bg-surface/70 px-3 py-1.5 text-start text-sm text-ink transition-colors hover:border-accent hover:bg-accent-soft/60 focus-visible:outline-2 focus-visible:outline-focus pointer-coarse:min-h-11"
            >
              <IconPlus className="size-3.5 shrink-0 text-accent" aria-hidden />
              <span className="min-w-0 truncate" dir="auto" data-user-content={chip.isUserContent ? true : undefined}>
                {chip.text}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
