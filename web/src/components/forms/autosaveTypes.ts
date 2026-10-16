/**
 * What a form that saves itself holds (AutosaveSnapshot) and what it is
 * told (AutosaveConfig): see autosaveEngine.ts.
 */

import type { ApiError } from "@/api/errors";
import type { MutationResult } from "@/api/mutations";

export type FieldSaveStatus = "idle" | "saving" | "saved" | "failed";

export interface FieldSaveState {
  status: FieldSaveStatus;
  /** When the field was last saved (clock time), for the "Saved" mark that fades. */
  savedAt: number | null;
}

export interface AutosaveSnapshot<Form, Stored> {
  form: Form;
  /** What the server holds, as last read or saved. */
  base: Stored;
  fields: Partial<Record<keyof Form, FieldSaveState>>;
  /** The last failed save, until one goes through. */
  error: ApiError | null;
  /** Fields someone else changed while they were edited here: they show the stored value. */
  conflicts: (keyof Form)[];
  /** A save was refused as stale and what is stored now could not be loaded either. */
  isReloadFailed: boolean;
  /** Fields whose change waits for the owner's confirmation. */
  confirming: (keyof Form)[];
  /** A save is running or waiting (typing, a retry). */
  isBusy: boolean;
}

export interface AutosaveConfig<Form, Stored, Body> {
  toForm: (stored: Stored) => Form;
  /** Fields that cannot be saved as they are (shown under them); they wait. */
  invalidFields?: (form: Form) => (keyof Form)[];
  /** The request for the changes from `base`, or null when there are none. */
  toBody: (form: Form, base: Stored) => Body | null;
  save: (body: Body, base: Stored) => Promise<MutationResult<Stored>>;
  /** Refusals because someone saved since: reload what is stored and put the form on top. */
  conflict?: {
    isConflict: (error: ApiError) => boolean;
    reload: () => Promise<MutationResult<Stored>>;
    rebase: (shown: Stored, latest: Stored, form: Form) => { form: Form; conflicts: (keyof Form)[] };
  };
  /** Fields whose change must be confirmed first (none: save). */
  needsConfirmation?: (form: Form, base: Stored) => (keyof Form)[];
  /** A copy of the stored data from elsewhere that may replace `base` (another tab, a switch on the page). */
  isNewer?: (candidate: Stored, base: Stored) => boolean;
  onSaved?: (stored: Stored, before: Form, after: Form) => void;
  /** Waits before the automatic retries of a save that could not reach the server. */
  retryDelaysMs?: readonly number[];
}
