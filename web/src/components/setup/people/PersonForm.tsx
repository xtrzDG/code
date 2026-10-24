"use client";

/**
 * "Someone else": a manager's name and how to reach them (WhatsApp, SMS or
 * e-mail). Enter in a field adds the person, not "Continue".
 */

import { useState, type FormEvent } from "react";

import type { Schema } from "@/api/types";
import { validateContact, type ContactError, type ManagerContactInput } from "@/app/b/[businessId]/settings/_lib/contacts";
import { Button, Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

type PersonChannel = "whatsapp" | "sms" | "email";
const PERSON_CHANNELS: readonly PersonChannel[] = ["whatsapp", "sms", "email"];

const ADDRESS_ERRORS: Record<ContactError, MessageKey> = {
  required: "tunnelTeam.people.errors.address",
  tooLong: "validation.tooLong",
  email: "tunnelTeam.people.errors.email",
  chatId: "tunnelTeam.people.errors.address",
  duplicate: "tunnelTeam.people.errors.duplicate",
};

export function PersonForm({
  contacts,
  language,
  isSaving,
  onAdd,
}: {
  contacts: readonly Schema<"ManagerContactView">[];
  language: string;
  isSaving: boolean;
  onAdd: (contact: ManagerContactInput) => Promise<boolean>;
}) {
  const { t } = useI18n();
  const [name, setName] = useState("");
  const [channel, setChannel] = useState<PersonChannel>("whatsapp");
  const [address, setAddress] = useState("");
  const [errors, setErrors] = useState<{ name?: MessageKey; address?: MessageKey }>({});
  const isEmail = channel === "email";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const found = validateContact({ name, channel, address, language }, contacts);
    const next = {
      name: found.name ? (found.name === "tooLong" ? ("validation.tooLong" as const) : ("tunnelTeam.people.errors.name" as const)) : undefined,
      address: found.address ? ADDRESS_ERRORS[found.address] : undefined,
    };
    setErrors(next);
    if (next.name || next.address) {
      return;
    }
    if (await onAdd({ name: name.trim(), channel, address: address.trim(), language })) {
      setName("");
      setAddress("");
    }
  };

  return (
    <form onSubmit={(event) => void submit(event)} noValidate data-enter="own" className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)_minmax(0,1.4fr)]">
        <Field label={t("tunnelTeam.people.name")} error={errors.name ? t(errors.name) : undefined}>
          {(control) => (
            <Input
              {...control}
              value={name}
              maxLength={100}
              dir="auto"
              autoComplete="off"
              placeholder={t("tunnelTeam.people.namePlaceholder")}
              onChange={(event) => {
                setName(event.target.value);
                setErrors((current) => ({ ...current, name: undefined }));
              }}
            />
          )}
        </Field>
        <Field label={t("tunnelTeam.people.channel")}>
          {(control) => (
            <Select {...control} value={channel} onChange={(event) => setChannel(event.target.value as PersonChannel)}>
              {PERSON_CHANNELS.map((option) => (
                <option key={option} value={option}>
                  {t(`tunnelTeam.people.channels.${option}`)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field
          label={isEmail ? t("tunnelTeam.people.email") : t("tunnelTeam.people.phone")}
          hint={isEmail ? undefined : t("tunnelTeam.people.phoneHint")}
          error={errors.address ? t(errors.address) : undefined}
        >
          {(control) => (
            <Input
              {...control}
              value={address}
              type={isEmail ? "email" : "tel"}
              inputMode={isEmail ? "email" : "tel"}
              autoComplete="off"
              dir="ltr"
              maxLength={254}
              onChange={(event) => {
                setAddress(event.target.value);
                setErrors((current) => ({ ...current, address: undefined }));
              }}
            />
          )}
        </Field>
      </div>
      <Button type="submit" variant="secondary" isLoading={isSaving} loadingText={t("tunnelTeam.people.adding")}>
        {t("tunnelTeam.people.addPerson")}
      </Button>
    </form>
  );
}
