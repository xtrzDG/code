"use client";

import { useState } from "react";

import type { ResourceKind } from "@/api/types";
import { Alert, Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  currencyFractionDigits,
  decimalInputValue,
  majorToMinor,
  minorToMajor,
  parseDecimalInput,
} from "@/lib/format";

import { NicheQuestions, useNicheAnswers } from "../NicheQuestions";
import { ResourcesSection } from "../ResourcesSection";
import { StepForm } from "../StepForm";
import type { StepProps } from "../types";

const RESOURCE_KINDS: Record<ResourceKind, MessageKey> = {
  table: "onboarding.booking.resourceKinds.table",
  room: "onboarding.booking.resourceKinds.room",
  staff: "onboarding.booking.resourceKinds.staff",
  arena: "onboarding.booking.resourceKinds.arena",
  bay: "onboarding.booking.resourceKinds.bay",
  vehicle: "onboarding.booking.resourceKinds.vehicle",
  slot: "onboarding.booking.resourceKinds.slot",
};

const MAX_SLOT_MINUTES = 43_200;
const MAX_NOTICE_MINUTES = 525_600;
const MAX_PARTY_SIZE = 10_000;

type BookingField = "slotMinutes" | "maxPartySize" | "minNotice" | "deposit";

function wholeNumber(text: string, min: number, max: number): number | null {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const value = Number(trimmed);
  return value >= min && value <= max ? value : null;
}

/** Step 4: what is booked, for how long, how many people, notice and deposit. */
export function BookingStep({
  wizard,
  step,
  canEdit,
  isSaving,
  isLastStep,
  onSave,
  onChange,
  onProgressChanged,
}: StepProps) {
  const { t } = useI18n();
  const { niche, profile } = wizard;
  const rules = profile.booking_rules;
  const currency = wizard.currency_code;
  const questions = step.questions ?? [];
  const answers = useNicheAnswers(questions, onChange);

  const [resourceKind, setResourceKind] = useState<ResourceKind>(rules?.resource_kind ?? niche.resource_kind);
  const [slotMinutes, setSlotMinutes] = useState(String(rules?.slot_minutes ?? (niche.booking_unit === "night" ? 1440 : 60)));
  const [maxPartySize, setMaxPartySize] = useState(rules ? String(rules.max_party_size) : "");
  const [minNotice, setMinNotice] = useState(String(rules?.min_notice_minutes ?? 0));
  const [deposit, setDeposit] = useState(
    rules?.deposit_minor
      ? decimalInputValue(minorToMajor(rules.deposit_minor, currency), currencyFractionDigits(currency))
      : "",
  );
  const [cancellation, setCancellation] = useState(rules?.cancellation_policy ?? "");
  const [errors, setErrors] = useState<Partial<Record<BookingField, MessageKey>>>({});

  const edit = (setter: (value: string) => void) => (value: string) => {
    setter(value);
    onChange();
  };

  const submit = (advance: boolean) => {
    const answersValid = answers.validate();
    if (!niche.takes_bookings) {
      if (answersValid) {
        void onSave({ answers: answers.payload() }, { advance });
      }
      return;
    }

    const found: Partial<Record<BookingField, MessageKey>> = {};
    const slot = wholeNumber(slotMinutes, 5, MAX_SLOT_MINUTES);
    const party = wholeNumber(maxPartySize, 1, MAX_PARTY_SIZE);
    const notice = wholeNumber(minNotice || "0", 0, MAX_NOTICE_MINUTES);
    const depositMajor = deposit.trim() === "" ? null : parseDecimalInput(deposit);
    if (slot === null) found.slotMinutes = "validation.positive";
    if (maxPartySize.trim() === "") found.maxPartySize = "validation.required";
    else if (party === null) found.maxPartySize = "validation.positive";
    if (notice === null) found.minNotice = "validation.wholeNumber";
    if (deposit.trim() !== "" && depositMajor === null) found.deposit = "validation.number";
    setErrors(found);
    if (Object.keys(found).length > 0 || !answersValid || slot === null || party === null || notice === null) {
      return;
    }

    void onSave(
      {
        booking_rules: {
          resource_kind: resourceKind,
          slot_minutes: slot,
          max_party_size: party,
          min_notice_minutes: notice,
          deposit_minor: depositMajor ? majorToMinor(depositMajor, currency) : null,
          deposit_currency_code: depositMajor ? currency : null,
          cancellation_policy: cancellation.trim() || null,
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
      {!niche.takes_bookings ? (
        <Alert tone="info">{t("onboarding.booking.noBookings")}</Alert>
      ) : (
        <div>
          <div className="grid gap-6 md:grid-cols-2">
            <Field label={t("onboarding.booking.resourceKind")}>
              {(control) => (
                <Select
                  {...control}
                  value={resourceKind}
                  onChange={(event) => {
                    setResourceKind(event.target.value as ResourceKind);
                    onChange();
                  }}
                >
                  {(Object.keys(RESOURCE_KINDS) as ResourceKind[]).map((kind) => (
                    <option key={kind} value={kind}>
                      {t(RESOURCE_KINDS[kind])}
                      {kind === niche.resource_kind ? ` (${niche.resource_noun})` : ""}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            {niche.booking_unit === "time_slot" ? (
              <Field
                label={t("onboarding.booking.slotMinutes")}
                hint={t("onboarding.booking.slotMinutesHint")}
                error={errors.slotMinutes && t(errors.slotMinutes)}
              >
                {(control) => (
                  <Input {...control} inputMode="numeric" value={slotMinutes} onChange={(event) => edit(setSlotMinutes)(event.target.value)} />
                )}
              </Field>
            ) : null}
            <Field label={t("onboarding.booking.maxPartySize")} required error={errors.maxPartySize && t(errors.maxPartySize)}>
              {(control) => (
                <Input {...control} inputMode="numeric" value={maxPartySize} onChange={(event) => edit(setMaxPartySize)(event.target.value)} />
              )}
            </Field>
            <Field label={t("onboarding.booking.minNotice")} error={errors.minNotice && t(errors.minNotice)}>
              {(control) => (
                <Input {...control} inputMode="numeric" value={minNotice} onChange={(event) => edit(setMinNotice)(event.target.value)} />
              )}
            </Field>
            <Field
              label={t("onboarding.booking.deposit", { currency })}
              hint={t("onboarding.booking.depositHint")}
              error={errors.deposit && t(errors.deposit)}
            >
              {(control) => (
                <Input {...control} inputMode="decimal" value={deposit} onChange={(event) => edit(setDeposit)(event.target.value)} />
              )}
            </Field>
            <Field label={t("onboarding.booking.cancellation")} className="md:col-span-2">
              {(control) => (
                <Input
                  {...control}
                  value={cancellation}
                  maxLength={1000}
                  placeholder={t("onboarding.booking.cancellationPlaceholder")}
                  onChange={(event) => edit(setCancellation)(event.target.value)}
                />
              )}
            </Field>
          </div>
        </div>
      )}

      {niche.takes_bookings ? (
        <ResourcesSection
          businessId={wizard.business_id}
          resourceKind={resourceKind}
          resourceNoun={niche.resource_noun}
          canEdit={canEdit}
          onChanged={onProgressChanged}
        />
      ) : null}

      <NicheQuestions questions={questions} state={answers} />
    </StepForm>
  );
}
