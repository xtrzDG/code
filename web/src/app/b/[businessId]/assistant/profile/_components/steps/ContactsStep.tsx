"use client";

import { useState } from "react";

import type { Weekday } from "@/api/types";
import { Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { webLinkSchema } from "@/lib/validation";

import { HoursEditor, hoursToRows, rowsToHours, type DayRows } from "../HoursEditor";
import { NicheQuestions, useNicheAnswers } from "../NicheQuestions";
import { StepForm, StepSection } from "../StepForm";
import type { StepProps } from "../types";

const MAX_ADDRESS_LENGTH = 500;

/** Step 2: address with a maps link, contact phones and opening hours. */
export function ContactsStep({ wizard, step, canEdit, isSaving, isLastStep, onSave, onChange }: StepProps) {
  const { t } = useI18n();
  const { profile } = wizard;
  const questions = step.questions ?? [];
  const answers = useNicheAnswers(questions, onChange);

  const [address, setAddress] = useState(profile.address?.text ?? "");
  const [mapsUrl, setMapsUrl] = useState(profile.address?.maps_url ?? "");
  const [publicPhone, setPublicPhone] = useState(profile.contacts.public_phone_number ?? "");
  const [handoffPhone, setHandoffPhone] = useState(profile.contacts.handoff_phone_number ?? "");
  const [days, setDays] = useState<DayRows[]>(() => hoursToRows(profile.hours ?? []));
  const [errors, setErrors] = useState<{ address?: MessageKey; mapsUrl?: MessageKey }>({});
  const [hoursErrors, setHoursErrors] = useState<Partial<Record<Weekday, MessageKey>>>({});

  const changed = <T,>(setter: (value: T) => void) => (value: T) => {
    setter(value);
    onChange();
  };

  const submit = (advance: boolean) => {
    const found: { address?: MessageKey; mapsUrl?: MessageKey } = {};
    if (mapsUrl.trim() !== "" && !webLinkSchema.safeParse(mapsUrl).success) {
      found.mapsUrl = "validation.url";
    }
    if (mapsUrl.trim() !== "" && address.trim() === "") {
      found.address = "validation.required";
    }
    const hours = rowsToHours(days);
    setErrors(found);
    setHoursErrors(hours.ok ? {} : hours.errors);
    const answersValid = answers.validate();
    if (Object.keys(found).length > 0 || !hours.ok || !answersValid) {
      return;
    }

    void onSave(
      {
        address: address.trim() ? { text: address.trim(), maps_url: mapsUrl.trim() || null } : null,
        hours: hours.hours,
        contacts: {
          public_phone_number: publicPhone.trim() || null,
          handoff_phone_number: handoffPhone.trim() || null,
        },
        answers: answers.payload(),
      },
      { advance },
    );
  };

  return (
    <StepForm
      title={step.title}
      description={step.description}
      canEdit={canEdit}
      isSaving={isSaving}
      isLastStep={isLastStep}
      onSubmit={submit}
    >
      <div className="grid gap-6 md:grid-cols-2">
        <Field label={t("onboarding.contacts.address")} error={errors.address && t(errors.address)} className="md:col-span-2">
          {(control) => (
            <Input
              {...control}
              value={address}
              maxLength={MAX_ADDRESS_LENGTH}
              autoComplete="street-address"
              placeholder={t("onboarding.contacts.addressPlaceholder")}
              onChange={(event) => changed(setAddress)(event.target.value)}
            />
          )}
        </Field>
        <Field
          label={t("onboarding.contacts.mapsUrl")}
          hint={t("onboarding.contacts.mapsUrlHint")}
          error={errors.mapsUrl && t(errors.mapsUrl)}
          className="md:col-span-2"
        >
          {(control) => (
            <Input
              {...control}
              type="url"
              inputMode="url"
              value={mapsUrl}
              placeholder="https://maps.google.com/…"
              onChange={(event) => changed(setMapsUrl)(event.target.value)}
            />
          )}
        </Field>
        <Field label={t("onboarding.contacts.publicPhone")} hint={t("onboarding.contacts.publicPhoneHint")}>
          {(control) => (
            <Input
              {...control}
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              value={publicPhone}
              onChange={(event) => changed(setPublicPhone)(event.target.value)}
            />
          )}
        </Field>
        <Field label={t("onboarding.contacts.handoffPhone")} hint={t("onboarding.contacts.handoffPhoneHint")}>
          {(control) => (
            <Input
              {...control}
              type="tel"
              inputMode="tel"
              value={handoffPhone}
              onChange={(event) => changed(setHandoffPhone)(event.target.value)}
            />
          )}
        </Field>
      </div>

      <StepSection title={t("onboarding.contacts.hours")} hint={t("onboarding.contacts.hoursHint", { timezone: wizard.timezone })}>
        <HoursEditor
          days={days}
          errors={hoursErrors}
          onChange={(next) => {
            setDays(next);
            setHoursErrors({});
            onChange();
          }}
        />
      </StepSection>

      <NicheQuestions questions={questions} state={answers} />
    </StepForm>
  );
}
