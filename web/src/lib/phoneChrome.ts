/**
 * What a page hands to the phone's compact chrome (components/ui/PhoneChrome):
 * the shell's top bar shows the page's description behind an (i) and its
 * live status as a dot, and the tab bar carries the page's primary action as
 * a floating button. Pages and their section frames register entries; the
 * deepest level wins the floating button and the live dot, and every
 * description is listed, the section's first.
 *
 * A tiny external store (useSyncExternalStore): pages write to it in
 * effects, only the bars read it, so a page never re-renders because its
 * own registration changed.
 */

/** 1: a page or a section frame of its own; 2: a page inside a section frame. */
export type ChromeLevel = 1 | 2;

export interface ChromeDescription<Node> {
  title: Node;
  text: Node;
}

export interface ChromeLive {
  /** When the page's data came from the server (ms; 0 while loading). */
  updatedAt: number;
  isFetching: boolean;
}

interface ChromeFab<Icon> {
  label: string;
  icon: Icon;
  /** Runs the page's latest handler (the registration keeps it fresh). */
  run: () => void;
  /** The action opens a dialog (aria-haspopup). */
  opensDialog?: boolean;
}

export interface ChromeEntry<Node, Icon> {
  level: ChromeLevel;
  description?: ChromeDescription<Node> | null;
  live?: ChromeLive | null;
  /** `null` hides the button of a shallower level (the page has its own way). */
  fab?: ChromeFab<Icon> | null;
}

export interface ChromeSnapshot<Node, Icon> {
  descriptions: ChromeDescription<Node>[];
  live: ChromeLive | null;
  fab: ChromeFab<Icon> | null;
}

/** The deepest entry that says something about `key` (undefined says nothing). */
function deepest<Node, Icon, Key extends "live" | "fab">(
  entries: readonly ChromeEntry<Node, Icon>[],
  key: Key,
): ChromeEntry<Node, Icon>[Key] | null {
  let found: ChromeEntry<Node, Icon> | null = null;
  for (const entry of entries) {
    if (entry[key] !== undefined && (found === null || entry.level >= found.level)) {
      found = entry;
    }
  }
  return (found?.[key] ?? null) as ChromeEntry<Node, Icon>[Key] | null;
}

/** What the bars show for the registered entries (in registration order). */
export function chromeSnapshot<Node, Icon>(entries: readonly ChromeEntry<Node, Icon>[]): ChromeSnapshot<Node, Icon> {
  const descriptions = [...entries]
    .filter((entry) => entry.description)
    .sort((left, right) => left.level - right.level)
    .map((entry) => entry.description as ChromeDescription<Node>);
  return { descriptions, live: deepest(entries, "live") ?? null, fab: deepest(entries, "fab") ?? null };
}

export const EMPTY_SNAPSHOT: ChromeSnapshot<never, never> = { descriptions: [], live: null, fab: null };

/** The registrations of the pages on screen, by registration id. */
export class ChromeStore<Node, Icon> {
  private readonly entries = new Map<string, ChromeEntry<Node, Icon>>();
  private readonly listeners = new Set<() => void>();
  private snapshot: ChromeSnapshot<Node, Icon> = EMPTY_SNAPSHOT;

  set(id: string, entry: ChromeEntry<Node, Icon>): void {
    this.entries.set(id, entry);
    this.publish();
  }

  remove(id: string): void {
    if (this.entries.delete(id)) {
      this.publish();
    }
  }

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  readonly getSnapshot = (): ChromeSnapshot<Node, Icon> => this.snapshot;

  private publish(): void {
    this.snapshot = chromeSnapshot([...this.entries.values()]);
    for (const listener of this.listeners) {
      listener();
    }
  }
}
