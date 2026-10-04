/**
 * "What's new": the cabinet's changelog entries (web/content/changelog) and
 * which of them a person has not read. The API keeps the newest key read
 * (PUT /v1/me/help/changelog); keys start with the date, so the newer entry
 * has the greater key. Someone who never opened "What's new" sees only the
 * newest entry as new, not the whole history.
 */

import type { Locale } from "@/i18n/config";

export interface ChangelogText {
  title: string;
  /** Paragraphs. */
  body: readonly string[];
}

export interface ChangelogEntry {
  /** "2026-10-04-help-center": the day it shipped, then a name. */
  key: string;
  texts: Readonly<Record<Locale, ChangelogText>>;
}

/** The API's ChangelogEntryKey. */
export const CHANGELOG_KEY = /^(\d{4})-(\d{2})-(\d{2})(-[a-z0-9]+)*$/;

export function newestFirst(entries: readonly ChangelogEntry[]): ChangelogEntry[] {
  return [...entries].sort((left, right) => (left.key < right.key ? 1 : left.key > right.key ? -1 : 0));
}

export function newestKey(entries: readonly ChangelogEntry[]): string | null {
  return newestFirst(entries)[0]?.key ?? null;
}

/** The entries newer than the last one read; without one, only the newest. */
export function unreadKeys(entries: readonly ChangelogEntry[], readKey: string | null | undefined): string[] {
  const sorted = newestFirst(entries);
  if (!readKey) {
    return sorted.slice(0, 1).map((entry) => entry.key);
  }
  return sorted.filter((entry) => entry.key > readKey).map((entry) => entry.key);
}

/** The day an entry shipped, as a Date at UTC midnight (format it with timeZone "UTC"); null for a bad key. */
export function entryDay(entry: Pick<ChangelogEntry, "key">): Date | null {
  const match = CHANGELOG_KEY.exec(entry.key);
  if (!match) {
    return null;
  }
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCMonth() === month - 1 && date.getUTCDate() === day ? date : null;
}
