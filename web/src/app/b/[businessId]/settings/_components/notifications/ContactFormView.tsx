"use client";

import { useState, type FormEvent } from "react";

import type { ApiError } from "@/api/errors";
import { useBusiness } from "@/components/business/BusinessContext";
import { Button, Field, Input, Select } from "@/components/ui";
import { InlineError } from "@/components/workspace/InlineError";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

import {
  contactFromForm,
  MAX_MANAGER_NAME_LENGTH,
  validateContact,
  type ContactError,
  type ContactField,
  type ContactForm,
  type ManagerContact,
  type ManagerContactChannel,
  type ManagerContactInput,
} from "../../_lib/contacts";
import { languageChoices } from "../../_lib/general";
import { ADDRESS_HINTS, ADDRESS_LABELS, CHANNEL_LABELS, CHANNELS, CONTACT_ERRORS, STALE_LIST_MESSAGES } from "./contactTexts";

/** A manager contact's name, channel, notification language and address. */
export function ContactFormView({
  initial,
  others,
  languages,
  isPending,
  error,
  onCancel,
  onSubmit,
}: {
  initial: ManagerContact | undefined;
  others: readonly ManagerContact[];
  languages: readonly string[];
  isPending: boolean;
  error: ApiError | null;
  onCancel: () => void;
  onSubmit: (contact: ManagerContactInput) => void;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const [form, setForm] = useState<ContactForm>({
    name: initial?.name ?? "",
    channel: initial?.channel ?? "email",
    address: initial?.address ?? "",
    language: initial?.language ?? business.owner_language,
  });
  const [errors, setErrors] = useState<Partial<Record<ContactField, ContactError>>>({});
  const languageOptions = languageChoices(languages, [form.language]);

  const update = (patch: Partial<ContactForm>) => {
    setForm((current) => ({ ...current, ...patch }));
    setErrors({});
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const found = validateContact(form, others);
    setErrors(found);
    if (Object.keys(found).length === 0) {
      onSubmit(contactFromForm(form));
    }
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      <Field label={t("settings.contacts.name")} required error={errors.name ? t(CONTACT_ERRORS[errors.name]) : undefined}>
        {(control) => (
          <Input
            {...control}
            value={form.name}
            dir="auto"
            maxLength={MAX_MANAGER_NAME_LENGTH}
            autoComplete="off"
            onChange={(event) => update({ name: event.target.value })}
          />
        )}
      </Field>
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t("settings.contacts.channel")}>
          {(control) => (
            <Select {...control} value={form.channel} onChange={(event) => update({ channel: event.target.value as ManagerContactChannel })}>
              {CHANNELS.map((channel) => (
                <option key={channel} value={channel}>
                  {t(CHANNEL_LABELS[channel])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field label={t("settings.contacts.language")}>
          {(control) => (
            <Select {...control} value={form.language} onChange={(event) => update({ language: event.target.value })}>
              {languageOptions.map((tag) => (
                <option key={tag} value={tag}>
                  {languageName(tag, locale)}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
      <Field
        label={t(ADDRESS_LABELS[form.channel])}
        hint={t(ADDRESS_HINTS[form.channel])}
        required
        error={errors.address ? t(CONTACT_ERRORS[errors.address]) : undefined}
      >
        {(control) => (
          <Input
            {...control}
            type={form.channel === "email" ? "email" : form.channel === "telegram" ? "text" : "tel"}
            inputMode={form.channel === "email" ? "email" : form.channel === "telegram" ? "numeric" : "tel"}
            dir="ltr"
            autoComplete="off"
            value={form.address}
            onChange={(event) => update({ address: event.target.value })}
          />
        )}
      </Field>
      <InlineError error={error} overrides={STALE_LIST_MESSAGES} />
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel} disabled={isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={isPending} loadingText={t("common.saving")}>
          {t("common.save")}
        </Button>
      </div>
    </form>
  );
}
