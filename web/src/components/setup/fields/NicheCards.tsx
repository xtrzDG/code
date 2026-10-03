"use client";

/**
 * "What do you do?": every kind of business the platform knows as a card
 * to pick (a group of radio buttons underneath, so the arrow keys move
 * between them and screen readers say "1 of 16, selected").
 */

import type { NicheSummaryView } from "@/api/types";
import { IconCheck } from "@/components/icons";
import { cn } from "@/lib/cn";

export function NicheCards({
  niches,
  value,
  onChange,
  legend,
  hint,
  error,
}: {
  niches: readonly NicheSummaryView[];
  value: string;
  onChange: (nicheKey: string) => void;
  legend: string;
  hint?: string;
  error?: string;
}) {
  const errorId = error ? "niche-cards-error" : undefined;
  return (
    <fieldset aria-describedby={errorId} className="min-w-0">
      <legend className="text-lg font-semibold text-ink">{legend}</legend>
      {hint ? <p className="mt-1 text-sm text-ink-muted">{hint}</p> : null}
      <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
        {niches.map((niche) => {
          const isChosen = niche.key === value;
          return (
            <label
              key={niche.key}
              className={cn(
                "group relative flex cursor-pointer items-start gap-3 rounded-2xl border bg-surface/80 p-3.5 backdrop-blur-sm transition-[border-color,background-color,transform,box-shadow] duration-(--motion-base) hover:-translate-y-0.5 hover:border-line-strong",
                "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-focus",
                isChosen
                  ? "border-accent bg-accent-soft/60 shadow-[0_14px_34px_-22px_var(--accent-solid)]"
                  : "border-line",
              )}
            >
              <input
                type="radio"
                name="niche"
                value={niche.key}
                checked={isChosen}
                onChange={() => onChange(niche.key)}
                className="peer sr-only"
              />
              <span className="min-w-0 flex-1">
                <span className="block text-sm leading-snug font-semibold text-ink">{niche.name}</span>
                <span className="mt-1 line-clamp-2 block text-xs text-ink-muted">{niche.description}</span>
              </span>
              <span
                aria-hidden
                className={cn(
                  "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border transition-colors",
                  isChosen ? "border-accent-solid bg-accent-solid text-on-accent" : "border-line-strong",
                )}
              >
                {isChosen ? <IconCheck className="size-3" /> : null}
              </span>
            </label>
          );
        })}
      </div>
      {error ? (
        <p id={errorId} className="mt-2 text-sm text-danger" role="alert">
          {error}
        </p>
      ) : null}
    </fieldset>
  );
}
