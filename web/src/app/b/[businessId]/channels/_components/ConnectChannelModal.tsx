"use client";

import { useState, type FormEvent } from "react";

import { useCountries } from "@/api/catalog";
import type { ErrorMessageOverrides } from "@/api/errors";
import { useBusiness } from "@/components/business/BusinessContext";
import { Button, Field, Input, Modal, Select } from "@/components/ui";
import { InlineError } from "@/components/workspace/InlineError";
import { useI18n } from "@/i18n/client";
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
import { CHANNEL_NAMES, CHANNEL_STEPS, FIELD_ERRORS, FIELD_LABELS } from "./channelMeta";

const SECRET_FIELDS: ReadonlySet<ConnectField> = new Set(["botToken", "pageAccessToken"]);
const NUMERIC_FIELDS: ReadonlySet<ConnectField> = new Set(["phoneNumberId", "businessAccountId", "pageId"]);
const OPTIONAL_FIELDS: ReadonlySet<ConnectField> = new Set(["businessAccountId", "countryHint"]);

/**
 * The connect (or update) form of one channel: the steps to get the
 * credentials and the fields the API needs for it.
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
      {kind ? <ConnectChannelForm
          key={kind}
          kind={kind}
          isPending={isPending}
          error={error}
          errorOverrides={errorOverrides}
          onClose={onClose}
          onSubmit={onSubmit}
        /> : null}
    </Modal>
  );
}

function ConnectChannelForm({
  kind,
  isPending,
  error,
  errorOverrides,
  onClose,
  onSubmit,
}: {
  kind: ConnectableChannel;
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
      <InlineError error={error} overrides={errorOverrides} />

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onClose} disabled={isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={isPending} loadingText={t("channels.connecting")}>
          {t("channels.submitConnect")}
        </Button>
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
