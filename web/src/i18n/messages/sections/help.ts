/**
 * Texts of help and support: the help center and its article drawer,
 * "Help and support" in the account panel, the one-time tips, "What's
 * new", the public status page with the cabinet's announcement banner, and
 * the platform admin's announcements.
 *
 * Top-level keys are namespaces. They are spread into en.ts, ru.ts and
 * ka.ts, so they must not clash with the namespaces of the other
 * dictionaries. `ru` and `ka` are type-checked against `en`.
 *
 * Each namespace lives in its own file per language under `./help/`; this
 * file composes them.
 */

import type { Translation } from "../../translate";
import { adminStatusEn } from "./help/adminStatus.en";
import { adminStatusKa } from "./help/adminStatus.ka";
import { adminStatusRu } from "./help/adminStatus.ru";
import { changelogEn } from "./help/changelog.en";
import { changelogKa } from "./help/changelog.ka";
import { changelogRu } from "./help/changelog.ru";
import { coachMarksEn } from "./help/coachMarks.en";
import { coachMarksKa } from "./help/coachMarks.ka";
import { coachMarksRu } from "./help/coachMarks.ru";
import { helpCenterEn } from "./help/helpCenter.en";
import { helpCenterKa } from "./help/helpCenter.ka";
import { helpCenterRu } from "./help/helpCenter.ru";
import { platformStatusEn } from "./help/platformStatus.en";
import { platformStatusKa } from "./help/platformStatus.ka";
import { platformStatusRu } from "./help/platformStatus.ru";

export const helpEn = {
  helpCenter: helpCenterEn,
  coachMarks: coachMarksEn,
  changelog: changelogEn,
  platformStatus: platformStatusEn,
  adminStatus: adminStatusEn,
} as const;

export const helpRu: Translation<typeof helpEn> = {
  helpCenter: helpCenterRu,
  coachMarks: coachMarksRu,
  changelog: changelogRu,
  platformStatus: platformStatusRu,
  adminStatus: adminStatusRu,
};

export const helpKa: Translation<typeof helpEn> = {
  helpCenter: helpCenterKa,
  coachMarks: coachMarksKa,
  changelog: changelogKa,
  platformStatus: platformStatusKa,
  adminStatus: adminStatusKa,
};
