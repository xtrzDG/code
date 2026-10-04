/**
 * "What's new" in the cabinet: one file per entry, named by its key (the
 * day it shipped, then a name), with its title and paragraphs in every
 * interface language. Add the newest entry here; the account menu shows a
 * dot until the person opens "What's new" (src/lib/help/changelog.ts).
 */

import type { ChangelogEntry } from "@/lib/help/changelog";

import { summaries } from "./2026-09-13-summaries";
import { phone } from "./2026-09-20-phone";
import { businessProfile } from "./2026-09-27-business-profile";
import { helpCenter } from "./2026-10-04-help-center";

export const CHANGELOG: readonly ChangelogEntry[] = [helpCenter, businessProfile, phone, summaries];
