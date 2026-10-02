"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { CHANNEL_LABELS, CUSTOMER_CHANNELS } from "@/components/insights/labels";
import type { BookingResult, ChannelKind, ManualBookingBody, ResourceView } from "@/components/insights/types";
import { Alert, Button, Field, Input, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

import {
  bookingUnitFor,
  validateBookingForm,
  type BookingFormErrors,
  type BookingFormValues,
} from "../_lib/manualBooking";
import { BOOKING_REFUSAL_MESSAGES } from "../_lib/bookingRefusals";
import { CustomerLanguageSelect } from "./CustomerLanguageSelect";
import { BookingCustomerFields } from "./BookingCustomerFields";
import { BookingTimingFields } from "./BookingTimingFields";

/**
 * A booking taken by phone or in person (POST …/bookings). The API checks
 * opening hours and free places; "Show free times" offers slots first.
 * The phone is read in the chosen country (the business country first).
 * From a conversation card the form is prefilled and the booking linked.
 */
export function BookingForm({
  resources,
  defaultDate,
  onCreated,
  onCancel,
  initialValues,
  conversationId,
}: {
  resources: readonly ResourceView[];
  defaultDate: string;
  onCreated: (result: BookingResult) => void;
  onCancel: () => void;
  initialValues?: Partial<BookingFormValues>;
  conversationId?: string;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
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
    country: business.country_code,
    ...initialValues,
  });
  const [errors, setErrors] = useState<BookingFormErrors>({});
  const unit = bookingUnitFor(resources, values.resourceId);

  const create = useMutation(
    (body: ManualBookingBody) =>
      api.POST("/v1/businesses/{business_id}/bookings", { params: { path: { business_id: businessId } }, body }),
    { errorMessages: { conflict: "bookings.errors.conflict" }, reasonMessages: BOOKING_REFUSAL_MESSAGES },
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
    const created = await create.run(
      conversationId ? { ...result.body, conversation_id: conversationId } : result.body,
    );
    if (created.ok) {
      onCreated(created.data);
    }
  };


  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      {activeResources.length === 0 ? (
        <Alert tone="info">
          <p>{t("bookings.form.noResources")}</p>
          <Link
            href={`${businessPath(businessId, "assistant/profile")}?step=booking_rules`}
            className="mt-1 inline-block font-medium text-accent hover:underline"
          >
            {t("bookings.form.toProfile")}
          </Link>
        </Alert>
      ) : null}
      <BookingCustomerFields values={values} errors={errors} set={set} />

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

      <BookingTimingFields
        values={values}
        errors={errors}
        unit={unit}
        set={set}
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
