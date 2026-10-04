"use client";

import { useState, type FormEvent } from "react";

import { useCountries } from "@/api/catalog";
import type { ErrorMessageOverrides } from "@/api/errors";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconChevronDown } from "@/components/icons";
import { Button, Field, Input, Modal, Select } from "@/components/ui";
import { InlineError } from "@/components/ui/InlineError";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { countryFlag } from "@/lib/countries";

import type { ConnectableChannel } from "../_lib/channels";
import {
  buildConnectBody,
  CHANNEL_FIELDS,
  EMPTY_CONNECT_FORM,
  type ConnectChannelBody,
  type ConnectField,
  type ConnectFieldError,
  type ConnectForm,
} from "../_lib/connectForm";
import { CHANNEL_NAMES, CHANNEL_STEPS, FIELD_ERRORS, FIELD_LABELS, META_INTROS } from "./channelMeta";
import { TelegramGuide } from "./TelegramGuide";

const SECRET_FIELDS: ReadonlySet<ConnectField> = new Set(["botToken", "pageAccessToken"]);
const NUMERIC_FIELDS: ReadonlySet<ConnectField> = new Set(["phoneNumberId", "businessAccountId", "pageId"]);
const OPTIONAL_FIELDS: ReadonlySet<ConnectField> = new Set(["businessAccountId", "countryHint"]);

/**
 * The connect (or update) form of one channel. Telegram is a guided walk
 * through @BotFather with the key checked as it is pasted; Meta's channels
 * (WhatsApp, Instagram, Messenger) say in plain words what they need and
 * keep their technical fields behind "Enter details manually"; the phone
 * asks for its number.
 */
export function ConnectChannelModal({
  kind,
  isReconnect,
  isPending,
  error,
  errorOverrides,
  onClose,
  onSubmit,
}: {
  kind: ConnectableChannel | null;
  isReconnect: boolean;
  isPending: boolean;
  error: unknown;
  errorOverrides?: ErrorMessageOverrides;
  onClose: () => void;
  onSubmit: (kind: ConnectableChannel, body: ConnectChannelBody) => Promise<boolean>;
}) {
  const { t } = useI18n();
  const name = kind ? t(CHANNEL_NAMES[kind]) : "";
  return (
    <Modal
      open={kind !== null}
      onClose={isPending ? () => undefined : onClose}
      title={isReconnect ? t("channels.reconnectTitle", { channel: name }) : t("channels.connectTitle", { channel: name })}
      size="md"
    >
      {kind === "telegram" ? (
        <TelegramGuide isPending={isPending} error={error} errorOverrides={errorOverrides} onClose={onClose} onSubmit={onSubmit} />
      ) : kind ? (
        <ConnectChannelForm
          key={kind}
          kind={kind}
          isReconnect={isReconnect}
          isPending={isPending}
          error={error}
          errorOverrides={errorOverrides}
          onClose={onClose}
          onSubmit={onSubmit}
        />
      ) : null}
    </Modal>
  );
}

function ConnectChannelForm({
  kind,
  isReconnect,
  isPending,
  error,
  errorOverrides,
  onClose,
  onSubmit,
}: {
  kind: ConnectableChannel;
  isReconnect: boolean;
  isPending: boolean;
  error: unknown;
  errorOverrides?: ErrorMessageOverrides;
  onClose: () => void;
  onSubmit: (kind: ConnectableChannel, body: ConnectChannelBody) => Promise<boolean>;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const fields = CHANNEL_FIELDS[kind];
  const steps = CHANNEL_STEPS[kind] ?? [];
  const [form, setForm] = useState<ConnectForm>({ ...EMPTY_CONNECT_FORM, countryHint: business.country_code });
  const [errors, setErrors] = useState<Partial<Record<ConnectField, ConnectFieldError>>>({});
  const intro = META_INTROS[kind];
  // Meta's ids and tokens are for those who know them: behind a click, open when updating.
  const [showManual, setShowManual] = useState(intro === undefined || isReconnect);

  const update = (field: ConnectField, value: string) => {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const result = buildConnectBody(kind, form);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    const ok = await onSubmit(kind, result.body);
    if (ok) {
      // Credentials never stay in memory longer than needed.
      setForm({ ...EMPTY_CONNECT_FORM, countryHint: business.country_code });
    }
  };

  const hasSecrets = fields.some((field) => SECRET_FIELDS.has(field));

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      {intro ? (
        <div className="space-y-3">
          <p className="text-sm text-ink-muted">{t(intro)}</p>
          <button
            type="button"
            aria-expanded={showManual}
            aria-controls={`connect-${kind}-manual`}
            onClick={() => setShowManual((current) => !current)}
            className="inline-flex items-center gap-1.5 rounded-lg text-sm font-medium text-accent hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            {showManual ? t("channelSetup.meta.hideManual") : t("channelSetup.meta.manual")}
            <IconChevronDown aria-hidden className={cn("size-4 transition-transform", showManual && "rotate-180")} />
          </button>
        </div>
      ) : null}

      {showManual ? (
        <div id={`connect-${kind}-manual`} className="space-y-5">
          {steps.length > 0 ? (
            <section aria-labelledby={`connect-${kind}-steps`} className="rounded-xl border border-line bg-surface-muted/60 p-4">
              <h3 id={`connect-${kind}-steps`} className="text-sm font-semibold text-ink">
                {t("channels.howTo")}
              </h3>
              <ol className="mt-2 list-decimal space-y-1.5 pl-5 text-sm text-ink-muted marker:text-ink-subtle">
                {steps.map((step) => (
                  <li key={step}>{t(step)}</li>
                ))}
              </ol>
            </section>
          ) : null}

          {fields.map((field) => {
            const labels = FIELD_LABELS[field];
            const error = errors[field];
            if (field === "countryHint") {
              return (
                <CountryHintField
                  key={field}
                  label={t(labels.label)}
                  hint={t(labels.hint)}
                  value={form.countryHint}
                  onChange={(value) => update("countryHint", value)}
                />
              );
            }
            return (
              <Field
                key={field}
                label={t(labels.label)}
                hint={t(labels.hint)}
                error={error ? t(FIELD_ERRORS[error]) : undefined}
                required={!OPTIONAL_FIELDS.has(field)}
                optionalLabel={OPTIONAL_FIELDS.has(field) ? t("common.optional") : undefined}
              >
                {(control) => (
                  <Input
                    {...control}
                    type={SECRET_FIELDS.has(field) ? "password" : field === "phoneNumber" ? "tel" : "text"}
                    inputMode={NUMERIC_FIELDS.has(field) ? "numeric" : field === "phoneNumber" ? "tel" : undefined}
                    autoComplete="off"
                    autoCapitalize="off"
                    spellCheck={false}
                    dir="ltr"
                    value={form[field]}
                    onChange={(event) => update(field, event.target.value)}
                  />
                )}
              </Field>
            );
          })}

          {hasSecrets ? <p className="text-xs text-ink-subtle">{t("channels.secretNote")}</p> : null}
        </div>
      ) : null}
      <InlineError error={error} overrides={errorOverrides} />

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onClose} disabled={isPending}>
          {t("common.cancel")}
        </Button>
        {showManual ? (
          <Button type="submit" isLoading={isPending} loadingText={t("channels.connecting")}>
            {t("channels.submitConnect")}
          </Button>
        ) : null}
      </div>
    </form>
  );
}

/** Country of a phone number typed without the country code (any country). */
function CountryHintField({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const { t } = useI18n();
  const countries = useCountries();
  return (
    <Field label={label} hint={hint} optionalLabel={t("common.optional")}>
      {(control) => (
        <Select {...control} value={value} onChange={(event) => onChange(event.target.value)} disabled={!countries.data}>
          {!countries.data ? <option value={value}>{value}</option> : null}
          {countries.data?.countries.map((country) => (
            <option key={country.country_code} value={country.country_code}>
              {`${countryFlag(country.country_code)} ${country.display_name} (+${country.calling_code})`}
            </option>
          ))}
        </Select>
      )}
    </Field>
  );
}
