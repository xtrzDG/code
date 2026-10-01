"use client";

import { useId } from "react";

import { cn } from "@/lib/cn";

/**
 * A single choice among a few options shown side by side (periods, tabs of
 * a list). Built on native radio buttons, so arrow keys move the choice and
 * screen readers announce "1 of 4".
 */
export function SegmentedControl<Value extends string>({
  label,
  value,
  options,
  onChange,
  className,
}: {
  /** Accessible name of the group (visually hidden). */
  label: string;
  value: Value;
  options: readonly { value: Value; label: string; count?: number }[];
  onChange: (value: Value) => void;
  className?: string;
}) {
  const name = useId();
  return (
    <fieldset className={cn("min-w-0", className)}>
      <legend className="sr-only">{label}</legend>
      <div className="flex max-w-full gap-1 overflow-x-auto rounded-xl border border-line bg-surface-muted p-1">
        {options.map((option) => {
          const checked = option.value === value;
          return (
            <label
              key={option.value}
              className={cn(
                "relative flex shrink-0 cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-colors",
                "has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-focus",
                checked ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink",
              )}
            >
              <input
                type="radio"
                name={name}
                value={option.value}
                checked={checked}
                onChange={() => onChange(option.value)}
                className="sr-only"
              />
              {option.label}
              {option.count !== undefined ? (
                <span
                  className={cn(
                    "rounded-full px-1.5 text-xs tabular-nums",
                    checked ? "bg-accent-soft text-accent-ink" : "bg-surface text-ink-subtle",
                  )}
                >
                  {option.count}
                </span>
              ) : null}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
