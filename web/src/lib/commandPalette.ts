/**
 * The command palette (Cmd/Ctrl+K) without React: its shortcut, the pages
 * it offers ("Go to"), matching typed text against them, the search it
 * sends to the API, and the keyboard moves through its one list of
 * results. "/" is not the palette's: it stays the inbox's search box.
 */

/** The groups of the palette's results, in the order they are listed. */
export const PALETTE_GROUPS = ["navigation", "customers", "conversations", "bookings"] as const;

export type PaletteGroup = (typeof PALETTE_GROUPS)[number];

/** One result: where it leads and how it reads. */
export interface PaletteEntry {
  id: string;
  group: PaletteGroup;
  label: string;
  /** A second line (a page's section, a customer's phone, a booking's time). */
  detail?: string;
  href: string;
}

/** A section or page of the navigation as the shell lists it. */
export interface PaletteNavLink {
  href: string;
  label: string;
  pages?: readonly { href: string; label: string }[];
}

/** Pages listed when nothing is typed, and at most after a match. */
export const NAVIGATION_LIMIT = 8;
/** Text shorter than this searches nothing (one letter finds everyone). */
const MIN_SEARCH_LENGTH = 2;
/** The API's limit for the search text. */
export const MAX_SEARCH_LENGTH = 100;

interface ShortcutEvent {
  key: string;
  metaKey: boolean;
  ctrlKey: boolean;
  altKey: boolean;
}

/** Cmd+K on a Mac, Ctrl+K elsewhere (both work everywhere); never "/" or K alone. */
export function isPaletteShortcut(event: ShortcutEvent): boolean {
  return (event.metaKey || event.ctrlKey) && !event.altKey && event.key.toLowerCase() === "k";
}

/** Text as matching compares it: lower case, without accents. */
export function foldText(text: string): string {
  return text.normalize("NFKD").replace(/\p{Mn}/gu, "").toLocaleLowerCase();
}

/** Every page of the navigation once: "Segments" with its section ("Customers") beside it. */
export function navigationEntries(links: readonly PaletteNavLink[]): PaletteEntry[] {
  const entries: PaletteEntry[] = [];
  const seen = new Set<string>();
  const add = (href: string, label: string, detail?: string) => {
    if (seen.has(href)) {
      return;
    }
    seen.add(href);
    entries.push({ id: `nav:${href}`, group: "navigation", label, detail, href });
  };
  for (const link of links) {
    const pages = link.pages ?? [];
    if (pages.length <= 1) {
      add(link.href, link.label);
      continue;
    }
    for (const page of pages) {
      add(page.href, page.label, page.label === link.label ? undefined : link.label);
    }
  }
  return entries;
}

/** The pages whose name (or section) holds every typed word, the first few. */
export function matchNavigation(entries: readonly PaletteEntry[], text: string): PaletteEntry[] {
  const words = foldText(text).split(/\s+/).filter(Boolean);
  const matches =
    words.length === 0
      ? entries
      : entries.filter((entry) => {
          const haystack = foldText(`${entry.label} ${entry.detail ?? ""}`);
          return words.every((word) => haystack.includes(word));
        });
  return matches.slice(0, NAVIGATION_LIMIT);
}

/** What the palette sends to the search: trimmed and cut to the API's limit; null for too little. */
export function searchTextOf(text: string): string | null {
  const trimmed = text.trim().slice(0, MAX_SEARCH_LENGTH).trim();
  return trimmed.length >= MIN_SEARCH_LENGTH ? trimmed : null;
}

/** Where ArrowUp/ArrowDown/Home/End move the highlight in a list of `count` (it wraps). */
export function movedIndex(current: number, count: number, key: string): number {
  if (count === 0) {
    return -1;
  }
  switch (key) {
    case "ArrowDown":
      return current < 0 ? 0 : (current + 1) % count;
    case "ArrowUp":
      return current <= 0 ? count - 1 : current - 1;
    case "Home":
      return 0;
    case "End":
      return count - 1;
    default:
      return current;
  }
}

/** The results in the order the list shows them (navigation first, then each group). */
export function orderedEntries(groups: Partial<Record<PaletteGroup, readonly PaletteEntry[]>>): PaletteEntry[] {
  return PALETTE_GROUPS.flatMap((group) => [...(groups[group] ?? [])]);
}
