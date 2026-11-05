/**
 * "What's new" in the cabinet: one file per entry, named by its key (the
 * day it shipped, then a name), with its title and paragraphs in every
 * interface language. Add the newest entry here; the account menu shows a
 * dot until the person opens "What's new" (src/lib/help/changelog.ts).
 * Empty until the first change after launch: the page then says so.
 */

import type { ChangelogEntry } from "@/lib/help/changelog";

export const CHANGELOG: readonly ChangelogEntry[] = [];
