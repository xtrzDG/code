"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { useCountries } from "@/api/catalog";
import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { CHANNEL_LABELS, CUSTOMER_CHANNELS } from "@/components/insights/labels";
import { withJsonBody } from "@/components/insights/requestBody";
import type { BookingResult, ChannelKind, ManualBookingBody, ResourceView } from "@/components/insights/types";
import { Alert, Button, Field, Input, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName, formatCallingCode } from "@/lib/countries";
import { businessPath } from "@/lib/navigation";

import { bookingUnitFor, validateBookingForm, type BookingFormErrors, type BookingFormValues } from "./bookingModel";
import { CustomerLanguageSelect } from "./CustomerLanguageSelect";
import { SlotPicker } from "./SlotPicker";

/**
 * A booking taken by phone or in person (POST …/bookings). The API checks
 * opening hours and free places; "Show free times" offers slots first.
 */
export function BookingForm({
  resources,
  defaultDate,
  onCreated,
  onCancel,
}: {
  resources: readonly ResourceView[];
  defaultDate: string;
  onCreated: (result: BookingResult) => void;
  onCancel: () => void;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const countries = useCountries();
  const businessId = business.id;
  const activeResources = resources.filter((resource) => resource.is_active);

  const [values, setValues] = useState<BookingFormValues>({
    contactName: "",
    phone: "",
    date: defaultDate,
    time: "",
    nights: "1",
    partySize: "2",
    resourceId: "",
    notes: "",
    source: "phone",
    language: business.default_language,
  });
  const [errors, setErrors] = useState<BookingFormErrors>({});
  const unit = bookingUnitFor(resources, values.resourceId);

  const create = useApiMutation(
    (body: ManualBookingBody) =>
      api.POST(
        "/v1/businesses/{business_id}/bookings",
        withJsonBody({ params: { path: { business_id: businessId } } }, body),
      ),
    { errorMessages: { conflict: "bookings.errors.conflict" } },
  );

  const set = <Key extends keyof BookingFormValues>(key: Key, value: BookingFormValues[Key]) => {
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const result = validateBookingForm(values, unit);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    const created = await create.run(result.body);
    if (created.ok) {
      onCreated(created.data);
    }
  };

  const country = countries.data?.countries.find((item) => item.country_code === business.country_code);
  const phoneHint = t("bookings.form.phoneHint", {
    country: [
      countryFlag(business.country_code),
      countryName(business.country_code, locale),
      country ? `(${formatCallingCode(country.calling_code)})` : null,
    ]
      .filter(Boolean)
      .join(" "),
  });
  const partySize = Number(values.partySize);
  const nights = Number(values.nights);

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      {activeResources.length === 0 ? (
        <Alert tone="info">
          <p>{t("bookings.form.noResources")}</p>
          <Link
            href={`${businessPath(businessId, "onboarding")}?step=booking_rules`}
            className="mt-1 inline-block font-medium text-accent hover:underline"
          >
            {t("bookings.form.toProfile")}
          </Link>
        </Alert>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("bookings.form.contactName")} error={errors.contactName && t(errors.contactName)} required>
          {(control) => (
            <Input
              {...control}
              dir="auto"
              autoComplete="off"
              value={values.contactName}
              maxLength={200}
              onChange={(event) => set("contactName", event.target.value)}
            />
          )}
        </Field>
        <Field
          label={t("bookings.form.phone")}
          hint={phoneHint}
          error={errors.phone && t(errors.phone)}
          optionalLabel={t("common.optional")}
        >
          {(control) => (
            <Input
              {...control}
              type="tel"
              dir="ltr"
              inputMode="tel"
              autoComplete="off"
              value={values.phone}
              maxLength={40}
              onChange={(event) => set("phone", event.target.value)}
            />
          )}
        </Field>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Field label={t("bookings.form.date")} error={errors.date && t(errors.date)} required>
          {(control) => (
            <Input {...control} type="date" value={values.date} onChange={(event) => set("date", event.target.value)} />
          )}
        </Field>
        <Field label={t("bookings.form.partySize")} error={errors.partySize && t(errors.partySize)} required>
          {(control) => (
            <Input
              {...control}
              type="number"
              inputMode="numeric"
              min={1}
              max={10000}
              value={values.partySize}
              onChange={(event) => set("partySize", event.target.value)}
            />
          )}
        </Field>
        <Field label={t("bookings.form.resource")}>
          {(control) => (
            <Select {...control} value={values.resourceId} onChange={(event) => set("resourceId", event.target.value)}>
              <option value="">{t("bookings.form.anyResource")}</option>
              {activeResources.map((resource) => (
                <option key={resource.id} value={resource.id}>
                  {resource.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>

      <div className="space-y-3 rounded-xl border border-line bg-surface-muted/50 p-4">
        <div className="grid gap-4 sm:grid-cols-3">
          {unit === "night" ? (
            <Field label={t("bookings.form.nights")} error={errors.nights && t(errors.nights)} required>
              {(control) => (
                <Input
                  {...control}
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={365}
                  value={values.nights}
                  onChange={(event) => set("nights", event.target.value)}
                />
              )}
            </Field>
          ) : (
            <Field label={t("bookings.form.time")} error={errors.time && t(errors.time)} required>
              {(control) => (
                <Input
                  {...control}
                  type="time"
                  step={300}
                  value={values.time}
                  onChange={(event) => set("time", event.target.value)}
                />
              )}
            </Field>
          )}
        </div>
        <SlotPicker
          request={{
            date: values.date,
            partySize: Number.isInteger(partySize) && partySize > 0 ? partySize : null,
            resourceId: values.resourceId || null,
            time: unit === "night" ? null : values.time || null,
            nights: unit === "night" && Number.isInteger(nights) && nights > 0 ? nights : null,
            isStay: unit === "night",
          }}
          selected={{ time: values.time || null, resourceId: values.resourceId || null }}
          onPick={(slot) => {
            setValues((current) => ({
              ...current,
              time: slot.time ?? current.time,
              resourceId: slot.resource_id,
              nights: slot.nights ? String(slot.nights) : current.nights,
            }));
            setErrors((current) => ({ ...current, time: undefined, nights: undefined }));
          }}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("bookings.form.source")}>
          {(control) => (
            <Select
              {...control}
              value={values.source}
              onChange={(event) => set("source", event.target.value as ChannelKind)}
            >
              {CUSTOMER_CHANNELS.map((channel) => (
                <option key={channel} value={channel}>
                  {t(CHANNEL_LABELS[channel])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <CustomerLanguageSelect value={values.language} onChange={(language) => set("language", language)} />
      </div>

      <Field label={t("bookings.form.notes")} error={errors.notes && t(errors.notes)} optionalLabel={t("common.optional")}>
        {(control) => (
          <Textarea
            {...control}
            dir="auto"
            rows={2}
            maxLength={1000}
            placeholder={t("bookings.form.notesPlaceholder")}
            value={values.notes}
            onChange={(event) => set("notes", event.target.value)}
          />
        )}
      </Field>

      <div className="flex flex-wrap justify-end gap-3 border-t border-line pt-4">
        <Button variant="secondary" onClick={onCancel} disabled={create.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={create.isPending} loadingText={t("bookings.form.submitting")}>
          {t("bookings.form.submit")}
        </Button>
      </div>
    </form>
  );
}
