"use client";

/**
 * A block of the Overview that a phone folds into one row: its name, a
 * short summary and a chevron; a tap opens it. Which rows a person opened
 * is remembered for them in this browser (`overview-open`). From large
 * screens the fold is not there at all: the block shows as it always did
 * (the wrapper takes no box, so grids place the block itself).
 *
 * A card inside names itself in the row: on a phone its own title is kept
 * for screen readers only, and its frame merges into the row's.
 */

import { createContext, useContext, useId, type ReactNode } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconChevronDown } from "@/components/icons";
import { cn } from "@/lib/cn";
import { parseNameSet, toggledNameSet } from "@/lib/userPreference";
import { useUserPreference } from "@/lib/useUserPreference";

const OPEN_FOLDS_PREFERENCE = "overview-open";

interface FoldState {
  isOpen: (name: string) => boolean;
  toggle: (name: string) => void;
}

const FoldContext = createContext<FoldState>({ isOpen: () => false, toggle: () => undefined });

/** The remembered open rows for every PhoneFold inside. */
export function PhoneFolds({ children }: { children: ReactNode }) {
  const { me } = useBusiness();
  const [stored, setStored] = useUserPreference(OPEN_FOLDS_PREFERENCE, me.user.id);
  const open = parseNameSet(stored);
  const state: FoldState = {
    isOpen: (name) => open.has(name),
    toggle: (name) => setStored(toggledNameSet(stored, name, !open.has(name))),
  };
  return <FoldContext.Provider value={state}>{children}</FoldContext.Provider>;
}

export function PhoneFold({
  name,
  title,
  summary,
  className,
  children,
}: {
  /** The row's key in the remembered set (lowercase letters, digits, dashes). */
  name: string;
  title: string;
  /** What the folded row says on the right (a total, the leading item). */
  summary?: string | null;
  className?: string;
  children: ReactNode;
}) {
  const folds = useContext(FoldContext);
  const id = useId();
  const isOpen = folds.isOpen(name);
  return (
    <div
      data-phone-fold={name}
      data-open={isOpen || undefined}
      className={cn("min-w-0 overflow-hidden rounded-2xl border border-line bg-surface lg:contents", className)}
    >
      <button
        type="button"
        aria-expanded={isOpen}
        aria-controls={id}
        onClick={() => folds.toggle(name)}
        className="flex min-h-13 w-full cursor-pointer items-center gap-3 px-4 py-3 text-start transition-colors hover:bg-surface-muted lg:hidden"
      >
        <span className="min-w-0 flex-1 text-[0.9375rem] font-semibold break-words text-ink">{title}</span>
        {summary ? <span className="max-w-[45%] shrink-0 text-end text-sm break-words text-ink-muted tabular-nums">{summary}</span> : null}
        <IconChevronDown
          className={cn("size-4 shrink-0 text-ink-subtle transition-transform", isOpen && "rotate-180")}
          aria-hidden
        />
      </button>
      <div
        id={id}
        className={cn(
          "max-lg:border-t max-lg:border-line lg:contents",
          // The card inside merges into the row: no second frame, its title said by the row.
          "max-lg:[&>section]:rounded-none max-lg:[&>section]:border-0 max-lg:[&_[data-card-title]]:sr-only max-lg:[&_[data-title-only]]:sr-only",
          !isOpen && "max-lg:hidden",
        )}
      >
        {children}
      </div>
    </div>
  );
}
