/**
 * Texts of help and support: the help center and its article drawer,
 * "Help and support" in the account panel, the one-time tips, "What's
 * new", the public status page with the cabinet's announcement banner, and
 * the platform admin's announcements.
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries. The other languages are type-checked against `en`.
 *
 * Each namespace lives in its own file per language under `./help/`; this
 * file composes them.
 */

import type { Translation } from "../../translate";
import { adminStatusEn } from "./help/adminStatus.en";
import { changelogEn } from "./help/changelog.en";
import { coachMarksEn } from "./help/coachMarks.en";
import { helpCenterEn } from "./help/helpCenter.en";
import { platformStatusEn } from "./help/platformStatus.en";
import { adminStatusIt } from "./help/adminStatus.it";
import { changelogIt } from "./help/changelog.it";
import { coachMarksIt } from "./help/coachMarks.it";
import { helpCenterIt } from "./help/helpCenter.it";
import { platformStatusIt } from "./help/platformStatus.it";

export const helpEn = {
  helpCenter: helpCenterEn,
  coachMarks: coachMarksEn,
  changelog: changelogEn,
  platformStatus: platformStatusEn,
  adminStatus: adminStatusEn,
} as const;

export const helpIt: Translation<typeof helpEn> = {
  helpCenter: helpCenterIt,
  coachMarks: coachMarksIt,
  changelog: changelogIt,
  platformStatus: platformStatusIt,
  adminStatus: adminStatusIt,
};
