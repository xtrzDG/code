"use client";

import Link from "next/link";
import { useId, type ReactNode } from "react";

import { Switch } from "@/components/content/Switch";
import { useBusiness } from "@/components/business/BusinessContext";
import { AutosaveHint } from "@/components/forms/AutosaveHint";
import { SavePill } from "@/components/forms/SavePill";
import type { FieldSaveState } from "@/components/forms/autosaveTypes";
import { useAutosaveForm } from "@/components/forms/useAutosaveForm";
import { Alert, ButtonLink, Card, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import {
  callSettingsBody,
  callSettingsForm,
  isSameCallSettings,
  READINESS_TEXTS,
  READINESS_TONES,
  templateNameError,
  textBackReadiness,
  turnedOffText,
  type CallSettingsBody,
  type CallSettingsForm,
  type CallSettingsView,
} from "../../_lib/calls";
import type { CallSettingsState } from "../../_lib/useCallSettings";

/**
 * The owner's choices: a summary after every call, and the message to a
 * caller who did not get through (which template, whether an SMS may
 * follow), with what such a caller would get right now. Every change
 * saves itself; switching something off offers Undo for a few seconds.
 */
export function CallSettingsFormCard({ stored, state }: { stored: CallSettingsView; state: CallSettingsState }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const { save, settings } = state;
  const form = useAutosaveForm<CallSettingsForm, CallSettingsView, CallSettingsBody>({
    stored,
    toForm: callSettingsForm,
    // A name Meta would refuse waits (with the stored one in the request) until it is valid.
    invalidFields: (values) => (templateNameError(values) ? ["templateName"] : []),
    toBody: (values, base) => (isSameCallSettings(values, base) ? null : callSettingsBody(values)),
    save: (body) => save.run(body),
    onSaved: (saved) => settings.setData(saved),
    undo: (before, after) => {
      const key = turnedOffText(before, after);
      return key ? t(key) : null;
    },
  });
  const { values } = form;
  const nameError = templateNameError(values);
  const readiness = textBackReadiness(values, form.stored);
  const pill = (field: keyof CallSettingsForm) => <SavePill state={form.fieldState(field)} onRetry={form.retry} />;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <AutosaveHint state={form.state} />
      </div>
      <Card title={t("callSettings.summaries.title")} description={t("callSettings.summaries.description")}>
        <SwitchRow
          label={t("callSettings.summaries.toggle")}
          checked={values.isSummaryEnabled}
          status={form.fieldState("isSummaryEnabled")}
          onRetry={form.retry}
          onChange={(isSummaryEnabled) => form.update("isSummaryEnabled", isSummaryEnabled)}
        />
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line pt-4">
          <p className="text-sm text-ink-muted">{t("callSettings.summaries.contactsHint")}</p>
          <ButtonLink href={businessPath(business.id, "settings/notifications")} variant="secondary" size="sm">
            {t("callSettings.summaries.openContacts")}
          </ButtonLink>
        </div>
      </Card>

      <Card title={t("callSettings.textBack.title")} description={t("callSettings.textBack.description")}>
        <div className="space-y-5">
          <SwitchRow
            label={t("callSettings.textBack.toggle")}
            checked={values.isTextBackEnabled}
            status={form.fieldState("isTextBackEnabled")}
            onRetry={form.retry}
            onChange={(isTextBackEnabled) => form.update("isTextBackEnabled", isTextBackEnabled)}
          />
          <Alert tone={READINESS_TONES[readiness]}>
            <p>{t(READINESS_TEXTS[readiness])}</p>
            {readiness !== "off" && !form.stored.is_whatsapp_connected ? (
              <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                <span>{t("callSettings.textBack.whatsappMissing")}</span>
                <Link
                  href={businessPath(business.id, "assistant/channels")}
                  className="font-medium text-accent underline underline-offset-2 hover:no-underline"
                >
                  {t("callSettings.textBack.connectWhatsapp")}
                </Link>
              </p>
            ) : null}
            {readiness !== "off" && !form.stored.is_sms_available ? (
              <p className="mt-1">{t("callSettings.textBack.smsMissing")}</p>
            ) : null}
          </Alert>
          <Field
            label={t("callSettings.textBack.template")}
            hint={t("callSettings.textBack.templateHint")}
            error={nameError ? t(nameError) : undefined}
            status={pill("templateName")}
          >
            {(control) => (
              <Input
                {...control}
                dir="ltr"
                autoComplete="off"
                spellCheck={false}
                placeholder="missed_call_text_back"
                value={values.templateName}
                onChange={(event) => form.type("templateName", event.target.value)}
                onBlur={form.flush}
              />
            )}
          </Field>
          {/* The SMS only follows a text-back message: with messages off it is not a choice. */}
          <SwitchRow
            label={t("callSettings.textBack.sms")}
            hint={values.isTextBackEnabled ? t("callSettings.textBack.smsHint") : t("callSettings.textBack.smsNeedsTextBack")}
            checked={values.isTextBackEnabled && values.isSmsFallbackEnabled}
            disabled={!values.isTextBackEnabled}
            status={form.fieldState("isSmsFallbackEnabled")}
            onRetry={form.retry}
            onChange={(isSmsFallbackEnabled) => form.update("isSmsFallbackEnabled", isSmsFallbackEnabled)}
          />
          <p className="text-sm text-ink-muted">{t("callSettings.textBack.rules")}</p>
        </div>
      </Card>
    </div>
  );
}

function SwitchRow({
  label,
  hint,
  checked,
  disabled = false,
  status,
  onRetry,
  onChange,
}: {
  label: string;
  hint?: ReactNode;
  checked: boolean;
  disabled?: boolean;
  status: FieldSaveState;
  onRetry: () => void;
  onChange: (checked: boolean) => void;
}) {
  const hintId = useId();
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <p className="text-sm font-medium text-ink">{label}</p>
          <SavePill state={status} onRetry={onRetry} />
        </div>
        {hint ? (
          <p id={hintId} className="mt-0.5 text-sm text-ink-muted">
            {hint}
          </p>
        ) : null}
      </div>
      <Switch checked={checked} onChange={onChange} label={label} disabled={disabled} describedBy={hint ? hintId : undefined} />
    </div>
  );
}
