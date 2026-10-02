"use client";

import { useCallback, useRef, useSyncExternalStore, type ComponentType, type KeyboardEvent, type ReactNode } from "react";

import { cn } from "@/lib/cn";

import { decodeHash } from "./helpers";
import type { IconProps } from "@/components/icons";

const HASH_EVENT = "aw:hashchange";

function subscribeToHash(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  window.addEventListener(HASH_EVENT, onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
    window.removeEventListener(HASH_EVENT, onChange);
  };
}

/** The location hash without "#", or "" (also on the server and for a malformed hash like "#%"). */
function readHash(): string {
  return typeof window === "undefined" ? "" : decodeHash(window.location.hash);
}

/**
 * The selected tab kept in the URL hash (`/settings#team`), so tabs can be
 * linked to and survive a reload. Unknown hashes select `fallback`.
 */
export function useHashTab<T extends string>(ids: readonly T[], fallback: T): [T, (id: T) => void] {
  const hash = useSyncExternalStore(subscribeToHash, readHash, () => "");
  const current = (ids as readonly string[]).includes(hash) ? (hash as T) : fallback;
  const select = useCallback((id: T) => {
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${window.location.search}#${id}`);
    window.dispatchEvent(new Event(HASH_EVENT));
  }, []);
  return [current, select];
}

export interface TabItem<T extends string> {
  id: T;
  label: string;
  icon?: ComponentType<IconProps>;
}

export function tabId(group: string, id: string): string {
  return `${group}-tab-${id}`;
}

export function tabPanelId(group: string, id: string): string {
  return `${group}-panel-${id}`;
}

/**
 * Accessible tabs (WAI-ARIA tab pattern): arrow keys move between tabs,
 * Home/End jump to the ends. The list scrolls sideways on phones.
 */
export function Tabs<T extends string>({
  group,
  items,
  value,
  onChange,
  label,
  className,
}: {
  /** Prefix of the element ids, unique on the page. */
  group: string;
  items: readonly TabItem<T>[];
  value: T;
  onChange: (id: T) => void;
  label: string;
  className?: string;
}) {
  const refs = useRef(new Map<T, HTMLButtonElement>());

  const focusTab = (index: number) => {
    const item = items[(index + items.length) % items.length];
    if (item) {
      onChange(item.id);
      refs.current.get(item.id)?.focus();
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const moves: Record<string, number> = {
      ArrowRight: index + 1,
      ArrowLeft: index - 1,
      Home: 0,
      End: items.length - 1,
    };
    const next = moves[event.key];
    if (next !== undefined) {
      event.preventDefault();
      focusTab(next);
    }
  };

  return (
    <div className={cn("-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0", className)}>
      <div role="tablist" aria-label={label} className="flex min-w-max gap-1 border-b border-line">
        {items.map((item, index) => {
          const selected = item.id === value;
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              ref={(element) => {
                if (element) {
                  refs.current.set(item.id, element);
                } else {
                  refs.current.delete(item.id);
                }
              }}
              type="button"
              role="tab"
              id={tabId(group, item.id)}
              aria-selected={selected}
              aria-controls={tabPanelId(group, item.id)}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(item.id)}
              onKeyDown={(event) => onKeyDown(event, index)}
              className={cn(
                "-mb-px inline-flex items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium whitespace-nowrap transition-colors",
                "focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-focus",
                selected
                  ? "border-accent-solid text-accent"
                  : "border-transparent text-ink-muted hover:border-line-strong hover:text-ink",
              )}
            >
              {Icon ? <Icon className="size-4" aria-hidden /> : null}
              {item.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

/** The content of one tab; render only the selected one. */
export function TabPanel({ group, id, children, className }: { group: string; id: string; children: ReactNode; className?: string }) {
  return (
    <div role="tabpanel" id={tabPanelId(group, id)} aria-labelledby={tabId(group, id)} tabIndex={0} className={cn("focus-visible:outline-none", className)}>
      {children}
    </div>
  );
}
