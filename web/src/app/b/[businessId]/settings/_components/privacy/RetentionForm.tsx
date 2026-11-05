"use client";

import Link from "next/link";

import { useBusiness } from "@/components/business/BusinessContext";
import { AutosaveHint } from "@/components/forms/AutosaveHint";
import { SavePill } from "@/components/forms/SavePill";
import { useAutosaveForm } from "@/components/forms/useAutosaveForm";
import { IconClock } from "@/components/icons";
import { ConfirmDialog, Field, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";
import { daysLabel, periodLabel } from "@/lib/retentionPeriods";

import {
  CONVERSATION_PERIODS,
  MODEL_RECORD_DAYS_MAX,
  MODEL_RECORD_PERIODS,
  RECOMMENDED_CONVERSATION_DAYS,
  isSameRetention,
  periodChoices,
  retentionBody,
  retentionForm,
  shorterPeriods,
  type PrivacySettingsBody,
  type PrivacySettingsView,
  type RetentionForm as RetentionFormValues,
} from "../../_lib/privacySettings";
import type { PrivacySettingsState } from "../../_lib/usePrivacySettings";
import { QualitySamplingSwitch } from "./QualitySamplingSwitch";
import { RetentionFacts } from "./RetentionFacts";

/**
 * The two periods an owner picks (conversations; the records of the
 * assistant's AI calls), what else follows them, and whether real
 * conversations join the nightly quality sample. Every choice saves
 * itself, except a shorter period: it deletes data at tonight's cleanup,
 * so it asks first (and goes back when not confirmed).
 */
export function RetentionForm({ stored, state }: { stored: PrivacySettingsView; state: PrivacySettingsState }) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const { save, settings } = state;
  const form = useAutosaveForm<RetentionFormValues, PrivacySettingsView, PrivacySettingsBody>({
    stored,
    toForm: retentionForm,
    toBody: (values, base) => (isSameRetention(values, base) ? null : retentionBody(values)),
    save: (body) => save.run(body),
    needsConfirmation: shorterPeriods,
    onSaved: (saved) => settings.setData(saved),
  });
  const { values } = form;
  const period = (days: number) => periodLabel(tp, days);
  const conversationLabel = (days: number) =>
    days === RECOMMENDED_CONVERSATION_DAYS ? t("privacyRetention.periods.recommended", { period: period(days) }) : period(days);
  // Model records are counted in days (the DPA's "30 days"), never "1 month".
  const modelRecordLabel = (days: number) => {
    const inDays = daysLabel(tp, days);
    return days === MODEL_RECORD_DAYS_MAX ? t("privacyRetention.periods.maximum", { period: inDays }) : inDays;
  };
  const pill = (field: keyof RetentionFormValues) => <SavePill state={form.fieldState(field)} onRetry={form.retry} />;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <AutosaveHint state={form.state} />
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        <Field label={t("privacyRetention.conversations.label")} hint={t("privacyRetention.conversations.hint")} status={pill("conversationDays")}>
          {(control) => (
            <Select
              {...control}
              value={String(values.conversationDays)}
              onChange={(event) => form.update("conversationDays", Number(event.target.value))}
            >
              {periodChoices(CONVERSATION_PERIODS, stored.conversation_retention_days).map((days) => (
                <option key={days} value={days}>
                  {conversationLabel(days)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("privacyRetention.modelRecords.label")} hint={t("privacyRetention.modelRecords.hint")} status={pill("modelRecordDays")}>
          {(control) => (
            <Select
              {...control}
              value={String(values.modelRecordDays)}
              onChange={(event) => form.update("modelRecordDays", Number(event.target.value))}
            >
              {periodChoices(MODEL_RECORD_PERIODS, stored.llm_turn_retention_days).map((days) => (
                <option key={days} value={days}>
                  {modelRecordLabel(days)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>

      <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-ink-muted">
        <IconClock className="size-4 shrink-0 text-ink-subtle" aria-hidden />
        <span>{t("privacyRetention.recordings", { period: period(stored.recording_retention_days) })}</span>
        <Link
          href={businessPath(business.id, "settings")}
          className="font-medium text-accent underline underline-offset-2 hover:no-underline"
        >
          {t("privacyRetention.changeRecordings")}
        </Link>
      </p>

      <RetentionFacts stored={stored} />

      <QualitySamplingSwitch
        checked={values.isQualitySamplingAllowed}
        status={pill("isQualitySamplingAllowed")}
        onChange={(allowed) => form.update("isQualitySamplingAllowed", allowed)}
      />

      <ConfirmDialog
        open={form.confirming.length > 0}
        onClose={form.cancelConfirmation}
        onConfirm={() => void form.confirm()}
        title={t("privacyRetention.shorterTitle")}
        description={t("privacyRetention.shorterDescription", {
          conversations: period(values.conversationDays),
          modelRecords: daysLabel(tp, values.modelRecordDays),
        })}
        confirmLabel={t("privacyRetention.shorterConfirm")}
      />
    </div>
  );
}
