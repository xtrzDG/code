"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { Switch } from "@/components/content/Switch";
import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, Button, ButtonLink, Card, Field, InlineError, Input, useToast } from "@/components/ui";
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
  type CallSettingsForm,
  type CallSettingsView,
} from "../../_lib/calls";
import type { CallSettingsState } from "../../_lib/useCallSettings";

/**
 * The owner's choices: a summary after every call, and the message to a
 * caller who did not get through (which template, whether an SMS may
 * follow), with what such a caller would get right now.
 */
export function CallSettingsFormCard({ stored, state }: { stored: CallSettingsView; state: CallSettingsState }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [form, setForm] = useState<CallSettingsForm>(() => callSettingsForm(stored));
  const [isChecked, setIsChecked] = useState(false);
  const { save, settings } = state;
  const nameError = isChecked ? templateNameError(form) : null;
  const readiness = textBackReadiness(form, stored);
  const update = (change: Partial<CallSettingsForm>) => setForm((current) => ({ ...current, ...change }));

  const submit = async () => {
    setIsChecked(true);
    if (templateNameError(form) !== null) {
      return;
    }
    const result = await save.run(callSettingsBody(form));
    if (result.ok) {
      settings.setData(result.data);
      setForm(callSettingsForm(result.data));
      setIsChecked(false);
      toast.success(t("callSettings.textBack.saved"));
    }
  };

  return (
    <form
      noValidate
      className="space-y-6"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <Card title={t("callSettings.summaries.title")} description={t("callSettings.summaries.description")}>
        <SwitchRow
          label={t("callSettings.summaries.toggle")}
          checked={form.isSummaryEnabled}
          disabled={save.isPending}
          onChange={(isSummaryEnabled) => update({ isSummaryEnabled })}
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
            checked={form.isTextBackEnabled}
            disabled={save.isPending}
            onChange={(isTextBackEnabled) => update({ isTextBackEnabled })}
          />
          <Alert tone={READINESS_TONES[readiness]}>
            <p>{t(READINESS_TEXTS[readiness])}</p>
            {readiness !== "off" && !stored.is_whatsapp_connected ? (
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
            {readiness !== "off" && !stored.is_sms_available ? (
              <p className="mt-1">{t("callSettings.textBack.smsMissing")}</p>
            ) : null}
          </Alert>
          <Field label={t("callSettings.textBack.template")} hint={t("callSettings.textBack.templateHint")} error={nameError ? t(nameError) : undefined}>
            {(control) => (
              <Input
                {...control}
                dir="ltr"
                autoComplete="off"
                spellCheck={false}
                placeholder="missed_call_text_back"
                value={form.templateName}
                disabled={save.isPending}
                onChange={(event) => update({ templateName: event.target.value })}
              />
            )}
          </Field>
          <SwitchRow
            label={t("callSettings.textBack.sms")}
            hint={t("callSettings.textBack.smsHint")}
            checked={form.isSmsFallbackEnabled}
            disabled={save.isPending}
            onChange={(isSmsFallbackEnabled) => update({ isSmsFallbackEnabled })}
          />
          <p className="text-sm text-ink-muted">{t("callSettings.textBack.rules")}</p>
        </div>
      </Card>

      <InlineError error={save.error} />
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={isSameCallSettings(form, stored)}
          isLoading={save.isPending}
          loadingText={t("common.saving")}
        >
          {t("callSettings.textBack.save")}
        </Button>
      </div>
    </form>
  );
}

function SwitchRow({
  label,
  hint,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  hint?: ReactNode;
  checked: boolean;
  disabled: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink">{label}</p>
        {hint ? <p className="mt-0.5 text-sm text-ink-muted">{hint}</p> : null}
      </div>
      <Switch checked={checked} onChange={onChange} label={label} disabled={disabled} />
    </div>
  );
}
