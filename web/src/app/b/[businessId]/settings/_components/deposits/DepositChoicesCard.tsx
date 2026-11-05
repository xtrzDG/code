"use client";

import { useState } from "react";

import { Switch } from "@/components/content/Switch";
import {
  depositSettingsBody,
  depositSettingsErrors,
  depositSettingsForm,
  type DepositSettingsForm,
} from "@/components/deposits/depositSettingsModel";
import type { DepositSettingsBody, DepositSettingsView } from "@/components/deposits/depositModel";
import { useDepositSettingsActions } from "@/components/deposits/useDeposits";
import { AutosaveHint } from "@/components/forms/AutosaveHint";
import { SavePill } from "@/components/forms/SavePill";
import { useAutosaveForm } from "@/components/forms/useAutosaveForm";
import { Alert, Card, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";

type NumberField = "holdMinutes" | "refundHours";

/**
 * Deposits on or off, how long a place waits for the payment and until
 * when a cancellation is refunded. Every change saves itself; a number
 * out of range waits (its error shows once the field is left), and
 * switching deposits off offers Undo. Payments are confirmed by hand.
 */
export function DepositChoicesCard({
  stored,
  onSaved,
}: {
  stored: DepositSettingsView;
  onSaved: (settings: DepositSettingsView) => void;
}) {
  const { t } = useI18n();
  const actions = useDepositSettingsActions();
  const [left, setLeft] = useState<readonly NumberField[]>([]);
  const form = useAutosaveForm<DepositSettingsForm, DepositSettingsView, DepositSettingsBody>({
    stored,
    toForm: depositSettingsForm,
    invalidFields: (values) => {
      const errors = depositSettingsErrors(values);
      return (["holdMinutes", "refundHours"] as const).filter((field) => errors[field] !== undefined);
    },
    toBody: depositSettingsBody,
    save: (body) => actions.save.run(body),
    onSaved: (saved) => onSaved(saved),
    undo: (before, after) => (before.isEnabled && !after.isEnabled ? t("deposits.settings.turnedOff") : null),
  });
  const { values } = form;
  const errors = depositSettingsErrors(values);
  const errorOf = (field: NumberField) => {
    const key = left.includes(field) ? errors[field] : undefined;
    return key ? t(key) : undefined;
  };
  const leave = (field: NumberField) => {
    setLeft((current) => (current.includes(field) ? current : [...current, field]));
    form.flush();
  };
  const pill = (field: keyof DepositSettingsForm) => <SavePill state={form.fieldState(field)} onRetry={form.retry} />;

  return (
    <Card
      title={t("deposits.settings.title")}
      actions={<AutosaveHint state={form.state} />}
    >
      <div className="space-y-5">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <p className="text-sm font-medium text-ink">{t("deposits.settings.toggle")}</p>
              {pill("isEnabled")}
            </div>
            <p className="text-sm text-ink-muted">{t("deposits.settings.toggleHint")}</p>
          </div>
          <Switch
            checked={values.isEnabled}
            onChange={(isEnabled) => form.update("isEnabled", isEnabled)}
            label={t("deposits.settings.toggle")}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label={t("deposits.settings.holdMinutes")}
            hint={t("deposits.settings.holdHint")}
            error={errorOf("holdMinutes")}
            status={pill("holdMinutes")}
          >
            {(control) => (
              <Input
                {...control}
                inputMode="numeric"
                autoComplete="off"
                value={values.holdMinutes}
                onChange={(event) => form.type("holdMinutes", event.target.value)}
                onBlur={() => leave("holdMinutes")}
              />
            )}
          </Field>
          <Field
            label={t("deposits.settings.refundHours")}
            hint={t("deposits.settings.refundHint")}
            error={errorOf("refundHours")}
            status={pill("refundHours")}
          >
            {(control) => (
              <Input
                {...control}
                inputMode="numeric"
                autoComplete="off"
                value={values.refundHours}
                onChange={(event) => form.type("refundHours", event.target.value)}
                onBlur={() => leave("refundHours")}
              />
            )}
          </Field>
        </div>
        <Alert tone="info">{t("deposits.settings.manual")}</Alert>
      </div>
    </Card>
  );
}
