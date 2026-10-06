"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { useAutosaveForm } from "@/components/forms/useAutosaveForm";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import {
  buildGeneralChanges,
  generalFormErrors,
  generalFormFrom,
  hasChanges,
  parseRetentionDays,
  type BusinessView,
  type GeneralError,
  type GeneralField,
  type GeneralForm,
  type SettingsChanges,
} from "./general";
import { changesFromRevision, isStaleRevision, rebaseGeneralForm } from "./revision";

const GENERAL_ERRORS: Record<GeneralError, MessageKey> = {
  required: "settings.general.errors.required",
  tooLong: "settings.general.errors.tooLong",
  languages: "settings.general.errors.languages",
  retention: "settings.general.errors.retention",
};

/**
 * The General form, saved by itself (useAutosaveForm): every change goes
 * with the business revision it was made from; a save refused because
 * someone saved since is put on top of what is stored now, and what nobody
 * else changed is saved again at once. A shorter recording retention
 * deletes recordings, so it asks first. `switched` is the business as the
 * status switch on the same page last saved it (a newer revision only).
 */
export function useGeneralSettings(initial: BusinessView, switched: BusinessView | null) {
  const { t } = useI18n();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const [dismissedConflicts, setDismissedConflicts] = useState("");
  const save = useMutation(
    (changes: SettingsChanges) =>
      api.PATCH("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } }, body: changes }),
    { errorToast: false },
  );
  const reload = useMutation(
    () => api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } } }),
    { errorToast: false },
  );

  const autosave = useAutosaveForm<GeneralForm, BusinessView, SettingsChanges>({
    stored: switched && switched.revision > initial.revision ? switched : initial,
    toForm: generalFormFrom,
    invalidFields: (form) => Object.keys(generalFormErrors(form)) as GeneralField[],
    toBody: (form, base) => {
      const built = buildGeneralChanges(base, form);
      return built.ok && hasChanges(built.changes) ? changesFromRevision(built.changes, base) : null;
    },
    save: (changes) => save.run(changes),
    isNewer: (candidate, base) => candidate.revision > base.revision,
    conflict: { isConflict: isStaleRevision, reload: () => reload.run(), rebase: rebaseGeneralForm },
    needsConfirmation: (form, base) => {
      const days = parseRetentionDays(form.retentionDays);
      return days !== null && days < base.recording_retention_days ? ["retentionDays"] : [];
    },
    onSaved: () => router.refresh(),
  });

  const errors = generalFormErrors(autosave.values);
  const conflictKey = autosave.conflicts.join(",");

  return {
    baseline: autosave.stored,
    form: autosave.values,
    state: autosave.state,
    disabled: !isOwner,
    /** Choices save at once; typed text a moment after the last key. */
    update: autosave.update,
    type: autosave.type,
    flush: autosave.flush,
    fieldState: autosave.fieldState,
    retry: autosave.retry,
    errorText: (field: GeneralField) => (errors[field] ? t(GENERAL_ERRORS[errors[field]]) : undefined),
    isStale: conflictKey !== "" && conflictKey !== dismissedConflicts,
    closeStale: () => setDismissedConflicts(conflictKey),
    isReloadFailed: autosave.isReloadFailed,
    isReloading: reload.isPending,
    loadCurrent: () => void autosave.reloadStored(),
    confirming: autosave.confirming.length > 0,
    confirm: () => void autosave.confirm(),
    cancelConfirmation: autosave.cancelConfirmation,
  };
}

export type GeneralSettings = ReturnType<typeof useGeneralSettings>;
