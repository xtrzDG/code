"use client";

import Link from "next/link";
import { useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconClock, IconShield } from "@/components/icons";
import { Button, ConfirmDialog, Field, InlineError, Select, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";
import { periodLabel } from "@/lib/retentionPeriods";

import {
  CONVERSATION_PERIODS,
  MODEL_RECORD_DAYS_MAX,
  MODEL_RECORD_PERIODS,
  RECOMMENDED_CONVERSATION_DAYS,
  isSameRetention,
  isShorterRetention,
  periodChoices,
  retentionBody,
  retentionForm,
  type PrivacySettingsView,
  type RetentionForm as RetentionFormValues,
} from "../../_lib/privacySettings";
import type { PrivacySettingsState } from "../../_lib/usePrivacySettings";
import { RetentionFacts } from "./RetentionFacts";

/**
 * The two periods an owner picks (conversations; the records of the
 * assistant's AI calls), what else follows them, and saving: a shorter
 * period deletes data at tonight's cleanup, so it asks first.
 */
export function RetentionForm({ stored, state }: { stored: PrivacySettingsView; state: PrivacySettingsState }) {
  const { t, tp } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [form, setForm] = useState<RetentionFormValues>(() => retentionForm(stored));
  const [isConfirming, setIsConfirming] = useState(false);
  const { save, settings } = state;
  const period = (days: number) => periodLabel(tp, days);
  const conversationLabel = (days: number) =>
    days === RECOMMENDED_CONVERSATION_DAYS
      ? t("privacyRetention.periods.recommended", { period: period(days) })
      : period(days);
  const modelRecordLabel = (days: number) =>
    days === MODEL_RECORD_DAYS_MAX ? t("privacyRetention.periods.maximum", { period: period(days) }) : period(days);

  const store = async () => {
    const result = await save.run(retentionBody(form));
    if (result.ok) {
      setIsConfirming(false);
      settings.setData(result.data);
      toast.success(t("privacyRetention.saved"));
    }
  };

  return (
    <form
      noValidate
      className="space-y-6"
      onSubmit={(event) => {
        event.preventDefault();
        if (isShorterRetention(form, stored)) {
          setIsConfirming(true);
          return;
        }
        void store();
      }}
    >
      <div className="grid gap-5 md:grid-cols-2">
        <Field label={t("privacyRetention.conversations.label")} hint={t("privacyRetention.conversations.hint")}>
          {(control) => (
            <Select
              {...control}
              value={String(form.conversationDays)}
              disabled={save.isPending}
              onChange={(event) => setForm((current) => ({ ...current, conversationDays: Number(event.target.value) }))}
            >
              {periodChoices(CONVERSATION_PERIODS, stored.conversation_retention_days).map((days) => (
                <option key={days} value={days}>
                  {conversationLabel(days)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("privacyRetention.modelRecords.label")} hint={t("privacyRetention.modelRecords.hint")}>
          {(control) => (
            <Select
              {...control}
              value={String(form.modelRecordDays)}
              disabled={save.isPending}
              onChange={(event) => setForm((current) => ({ ...current, modelRecordDays: Number(event.target.value) }))}
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

      <InlineError error={isConfirming ? null : save.error} />
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={isSameRetention(form, stored)}
          isLoading={save.isPending && !isConfirming}
          loadingText={t("common.saving")}
          leadingIcon={<IconShield className="size-4" aria-hidden />}
        >
          {t("privacyRetention.save")}
        </Button>
      </div>

      <ConfirmDialog
        open={isConfirming}
        onClose={() => setIsConfirming(false)}
        onConfirm={store}
        isPending={save.isPending}
        error={save.error}
        title={t("privacyRetention.shorterTitle")}
        description={t("privacyRetention.shorterDescription", {
          conversations: period(form.conversationDays),
          modelRecords: period(form.modelRecordDays),
        })}
        confirmLabel={t("privacyRetention.shorterConfirm")}
        pendingLabel={t("common.saving")}
      />
    </form>
  );
}
