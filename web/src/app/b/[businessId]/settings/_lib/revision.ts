/**
 * Concurrent saves of the Settings page: saves carry the revision they were
 * made from, and a save refused as stale is rebased on the stored business.
 */

import type { ApiError } from "@/api/errors";

import {
  generalFormFrom,
  sameList,
  type BusinessView,
  type GeneralField,
  type GeneralForm,
  type SettingsChanges,
} from "./general";

/** The API's reason for a settings save made from an older revision of the business. */
const STALE_REVISION_REASON = "stale_revision";

/**
 * The PATCH body for changes made to `business` as it was shown: the API
 * applies them only while nobody has saved the business since (another
 * owner, another tab, a manager added by the Telegram bot).
 */
export function changesFromRevision(changes: SettingsChanges, business: Pick<BusinessView, "revision">): SettingsChanges {
  return { ...changes, expected_revision: business.revision };
}

/** True when a save was refused because the business changed after it was shown. */
export function isStaleRevision(error: ApiError): boolean {
  return error.status === 409 && error.reasons.some((reason) => reason.code === STALE_REVISION_REASON);
}

/**
 * The business the General form edits after this tab's own status switch
 * (`switched`: the view that save returned). The switch changes no field of
 * the form, so the form takes over its newer revision. If form fields differ
 * too, someone else saved in between: the form keeps what it loaded, and its
 * next save is refused as stale (it then reloads) instead of overwriting.
 */
export function afterStatusSwitch(loaded: BusinessView, switched: BusinessView | null): BusinessView {
  if (!switched || switched.revision <= loaded.revision) {
    return loaded;
  }
  const isSameForm = JSON.stringify(generalFormFrom(switched)) === JSON.stringify(generalFormFrom(loaded));
  return isSameForm ? switched : loaded;
}

export interface RebasedGeneralForm {
  form: GeneralForm;
  /** Fields changed both here and elsewhere: they now show the stored value. */
  conflicts: GeneralField[];
}

function sameFormValue(left: GeneralForm[GeneralField], right: GeneralForm[GeneralField]): boolean {
  return Array.isArray(left) && Array.isArray(right) ? sameList(left, right) : left === right;
}

/**
 * After a save refused as stale: the business as stored now (`latest`)
 * with the owner's own changes (the form against `shown`) on top. A field
 * someone else changed too takes the stored value and is reported; a
 * revision raised by an unrelated save (a manager linked, billing) keeps
 * everything that was typed.
 */
export function rebaseGeneralForm(shown: BusinessView, latest: BusinessView, form: GeneralForm): RebasedGeneralForm {
  const before = generalFormFrom(shown);
  const stored = generalFormFrom(latest);
  const next: Record<GeneralField, GeneralForm[GeneralField]> = { ...stored };
  const conflicts: GeneralField[] = [];
  for (const field of Object.keys(before) as GeneralField[]) {
    if (sameFormValue(form[field], before[field])) {
      continue;
    }
    if (sameFormValue(stored[field], before[field]) || sameFormValue(stored[field], form[field])) {
      next[field] = form[field];
    } else {
      conflicts.push(field);
    }
  }
  return { form: next as unknown as GeneralForm, conflicts };
}
