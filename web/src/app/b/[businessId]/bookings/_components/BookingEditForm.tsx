"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import type { BookingUpdateBody, BookingView, ResourceView } from "@/components/insights/types";
import { Alert, Button, Field, Input, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  BOOKING_REFUSAL_MESSAGES,
  bookingEditValues,
  canChangePlacement,
  placesForEdit,
  validateBookingEdit,
  type BookingEditErrors,
  type BookingEditValues,
} from "./bookingModel";

/**
 * Changes the details of a booking (PATCH …/bookings/{id}): the customer's
 * name, party size, place and notes. The API checks that the place seats
 * the party and is free and open at the booked time; the time itself is
 * changed with "Move".
 */
export function BookingEditForm({
  booking,
  resources,
  onSaved,
  onCancel,
}: {
  booking: BookingView;
  resources: readonly ResourceView[];
  onSaved: (booking: BookingView | null) => void;
  onCancel: () => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const [values, setValues] = useState<BookingEditValues>(() => bookingEditValues(booking));
  const [errors, setErrors] = useState<BookingEditErrors>({});
  const placement = canChangePlacement(booking.status);
  const places = placesForEdit(resources, booking);

  const save = useApiMutation(
    (body: BookingUpdateBody) =>
      api.PATCH("/v1/businesses/{business_id}/bookings/{booking_id}", {
        params: { path: { business_id: business.id, booking_id: booking.id } },
        body,
      }),
    { errorMessages: { conflict: "bookings.errors.placeTaken" }, reasonMessages: BOOKING_REFUSAL_MESSAGES },
  );

  const set = <Key extends keyof BookingEditValues>(key: Key, value: BookingEditValues[Key]) => {
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const result = validateBookingEdit(values, booking);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    if (result.body === null) {
      onSaved(null);
      return;
    }
    const saved = await save.run(result.body);
    if (saved.ok) {
      onSaved(saved.data);
    }
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      {placement ? null : <Alert tone="info">{t("bookings.edit.finishedNote")}</Alert>}
      <Field label={t("bookings.form.contactName")} error={errors.contactName && t(errors.contactName)}>
        {(control) => (
          <Input
            {...control}
            dir="auto"
            autoComplete="off"
            maxLength={200}
            value={values.contactName}
            onChange={(event) => set("contactName", event.target.value)}
          />
        )}
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label={t("bookings.form.partySize")}
          hint={placement ? t("bookings.edit.partyHint") : undefined}
          error={errors.partySize && t(errors.partySize)}
        >
          {(control) => (
            <Input
              {...control}
              type="number"
              inputMode="numeric"
              min={1}
              max={10000}
              disabled={!placement}
              value={values.partySize}
              onChange={(event) => set("partySize", event.target.value)}
            />
          )}
        </Field>
        <Field label={t("bookings.form.resource")} hint={placement ? t("bookings.edit.placeHint") : undefined}>
          {(control) => (
            <Select
              {...control}
              disabled={!placement}
              value={values.resourceId}
              onChange={(event) => set("resourceId", event.target.value)}
            >
              {places.length === 0 ? <option value={booking.resource_id}>{booking.resource_name}</option> : null}
              {places.map((resource) => (
                <option key={resource.id} value={resource.id}>
                  {resource.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
      <Field label={t("bookings.form.notes")} error={errors.notes && t(errors.notes)} optionalLabel={t("common.optional")}>
        {(control) => (
          <Textarea
            {...control}
            dir="auto"
            rows={3}
            maxLength={1000}
            placeholder={t("bookings.form.notesPlaceholder")}
            value={values.notes}
            onChange={(event) => set("notes", event.target.value)}
          />
        )}
      </Field>
      <div className="flex flex-wrap justify-end gap-3 border-t border-line pt-4">
        <Button variant="secondary" onClick={onCancel} disabled={save.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={save.isPending} loadingText={t("bookings.edit.saving")}>
          {t("bookings.edit.save")}
        </Button>
      </div>
    </form>
  );
}
