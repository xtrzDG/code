"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import {
  buildGeneralChanges,
  generalFormFrom,
  hasChanges,
  type BusinessView,
  type GeneralError,
  type GeneralField,
  type GeneralForm,
  type SettingsChanges,
} from "./general";
import { afterStatusSwitch, changesFromRevision, isStaleRevision, rebaseGeneralForm } from "./revision";

const GENERAL_ERRORS: Record<GeneralError, MessageKey> = {
  required: "settings.general.errors.required",
  tooLong: "settings.general.errors.tooLong",
  languages: "settings.general.errors.languages",
  retention: "settings.general.errors.retention",
};

/**
 * The General form's values and its save. Saves carry the business revision
 * they were made from; a save refused because someone saved since is put on
 * top of what is stored now and saved again at once when nobody else changed
 * the same fields.
 */
export function useGeneralSettings(initial: BusinessView, switched: BusinessView | null) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business, isOwner } = useBusiness();
  const [loaded, setLoaded] = useState<BusinessView>(initial);
  const [form, setForm] = useState<GeneralForm>(() => generalFormFrom(initial));
  const [errors, setErrors] = useState<Partial<Record<GeneralField, GeneralError>>>({});
  const [isStale, setStale] = useState(false);
  // Refused as stale, but what is stored now could not be loaded either.
  const [isReloadFailed, setReloadFailed] = useState(false);
  // The status switch changes no field of this form, only the revision.
  const baseline = afterStatusSwitch(loaded, switched);

  const save = useApiMutation(
    (changes: SettingsChanges) =>
      api.PATCH("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } }, body: changes }),
    { errorToast: false },
  );
  // Both a refused answer and a network failure come back as a result.
  const reload = useApiMutation(
    () => api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: business.id } } }),
    { errorToast: false },
  );

  const result = buildGeneralChanges(baseline, form);
  const isDirty = !result.ok || hasChanges(result.changes);
  const disabled = !isOwner || save.isPending || reload.isPending;

  const update = <Field extends GeneralField>(field: Field, value: GeneralForm[Field]) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const saved = (stored: BusinessView) => {
    setLoaded(stored);
    setForm(generalFormFrom(stored));
    router.refresh();
    toast.success(t("settings.general.saved"));
  };

  /**
   * Save `typed` (made from `base`). Refused because someone saved since:
   * put it on top of what is stored now, and save once more when nobody
   * else changed the same fields.
   */
  const store = async (base: BusinessView, typed: GeneralForm, mayRetry: boolean): Promise<void> => {
    const built = buildGeneralChanges(base, typed);
    if (!built.ok) {
      setErrors(built.errors);
      return;
    }
    if (!hasChanges(built.changes)) {
      // What was typed is what is stored now.
      saved(base);
      return;
    }
    const answer = await save.run(changesFromRevision(built.changes, base));
    if (answer.ok) {
      saved(answer.data);
      return;
    }
    if (!isStaleRevision(answer.error)) {
      toast.error(answer.error);
      return;
    }
    const latest = await reload.run();
    router.refresh();
    if (!latest.ok) {
      // Do not claim the form shows what is stored: it still shows the
      // owner's own (refused) changes.
      setReloadFailed(true);
      toast.show({ tone: "error", title: t("settings.general.staleTitle") });
      return;
    }
    const rebased = rebaseGeneralForm(base, latest.data, typed);
    setLoaded(latest.data);
    setForm(rebased.form);
    setErrors({});
    if (rebased.conflicts.length === 0 && mayRetry) {
      await store(latest.data, rebased.form, false);
      return;
    }
    setStale(true);
    toast.show({ tone: "error", title: t("settings.general.staleTitle") });
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    if (!hasChanges(result.changes)) {
      toast.info(t("settings.general.noChanges"));
      return;
    }
    setStale(false);
    setReloadFailed(false);
    await store(baseline, form, true);
  };

  const loadCurrent = async () => {
    const latest = await reload.run();
    if (!latest.ok) {
      toast.error(latest.error);
      return;
    }
    const rebased = rebaseGeneralForm(baseline, latest.data, form);
    setLoaded(latest.data);
    setForm(rebased.form);
    setErrors({});
    setReloadFailed(false);
    setStale(true);
    router.refresh();
  };

  const discard = () => {
    setForm(generalFormFrom(baseline));
    setErrors({});
  };

  const errorText = (field: GeneralField) => (errors[field] ? t(GENERAL_ERRORS[errors[field]]) : undefined);

  return {
    baseline,
    form,
    update,
    errorText,
    isDirty,
    disabled,
    isSaving: save.isPending,
    isReloading: reload.isPending,
    isStale,
    closeStale: () => setStale(false),
    isReloadFailed,
    onSubmit,
    loadCurrent,
    discard,
  };
}

export type GeneralSettings = ReturnType<typeof useGeneralSettings>;
