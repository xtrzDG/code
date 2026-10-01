"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface TabItem<Key extends string> {
  key: Key;
  label: ReactNode;
}

/**
 * In-page tabs (WAI-ARIA tablist): arrow keys, Home and End move between
 * tabs; only the selected panel is rendered.
 */
export function Tabs<Key extends string>({
  label,
  tabs,
  selected,
  onSelect,
  children,
  className,
}: {
  label: string;
  tabs: readonly TabItem<Key>[];
  selected: Key;
  onSelect: (key: Key) => void;
  /** The selected tab's panel. */
  children: ReactNode;
  className?: string;
}) {
  const id = useId();
  const buttons = useRef<Map<Key, HTMLButtonElement>>(new Map());

  const move = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = tabs.length - 1;
    const target =
      event.key === "ArrowRight"
        ? index === last
          ? 0
          : index + 1
        : event.key === "ArrowLeft"
          ? index === 0
            ? last
            : index - 1
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? last
              : null;
    if (target === null) {
      return;
    }
    event.preventDefault();
    const tab = tabs[target];
    if (tab) {
      onSelect(tab.key);
      buttons.current.get(tab.key)?.focus();
    }
  };

  return (
    <div className={className}>
      <div className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
        <div role="tablist" aria-label={label} className="flex min-w-max gap-1 rounded-xl bg-surface-muted p-1">
          {tabs.map((tab, index) => {
            const isSelected = tab.key === selected;
            return (
              <button
                key={tab.key}
                ref={(node) => {
                  if (node) {
                    buttons.current.set(tab.key, node);
                  } else {
                    buttons.current.delete(tab.key);
                  }
                }}
                type="button"
                role="tab"
                id={`${id}-tab-${tab.key}`}
                aria-selected={isSelected}
                aria-controls={`${id}-panel`}
                tabIndex={isSelected ? 0 : -1}
                onClick={() => onSelect(tab.key)}
                onKeyDown={(event) => move(event, index)}
                className={cn(
                  "inline-flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-medium whitespace-nowrap transition-colors",
                  "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus",
                  isSelected ? "bg-surface text-ink shadow-sm" : "text-ink-muted hover:text-ink",
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>
      <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-tab-${selected}`} className="mt-4">
        {children}
      </div>
    </div>
  );
}
