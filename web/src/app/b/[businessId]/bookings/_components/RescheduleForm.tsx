"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { isLocalDate, isLocalTime } from "@/components/insights/dates";
import type { BookingResult, BookingView, RescheduleBookingBody } from "@/components/insights/types";
import { Button, Field, Input } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { customerLanguage } from "./bookingModel";
import { CustomerLanguageSelect } from "./CustomerLanguageSelect";
import { SlotPicker } from "./SlotPicker";

/** Moves a booking to a new date (and time for slots) on the same place: POST …/reschedule. */
export function RescheduleForm({
  booking,
  isStay,
  onDone,
  onCancel,
}: {
  booking: BookingView;
  /** Night bookings keep their length and move by date only. */
  isStay: boolean;
  onDone: (result: BookingResult) => void;
  onCancel: () => void;
}) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const businessId = business.id;
  const [language, setLanguage] = useState(customerLanguage(booking, business));
  const [date, setDate] = useState(booking.date);
  const [time, setTime] = useState(booking.time ?? "");
  const [errors, setErrors] = useState<{ date?: MessageKey; time?: MessageKey }>({});

  const reschedule = useApiMutation(
    (body: RescheduleBookingBody) =>
      api.POST("/v1/businesses/{business_id}/bookings/{booking_id}/reschedule", {
        params: { path: { business_id: businessId, booking_id: booking.id }, query: { language } },
        body,
      }),
    { errorMessages: { conflict: "bookings.errors.conflict" } },
  );

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const nextErrors: typeof errors = {};
    if (!isLocalDate(date)) nextErrors.date = "bookings.errors.dateRequired";
    if (!isStay && !isLocalTime(time)) nextErrors.time = "bookings.errors.timeRequired";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }
    const result = await reschedule.run({ new_date: date, new_time: isStay ? null : time });
    if (result.ok) {
      onDone(result.data);
    }
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("bookings.reschedule.newDate")} error={errors.date && t(errors.date)} required>
          {(control) => <Input {...control} type="date" value={date} onChange={(event) => setDate(event.target.value)} />}
        </Field>
        {isStay ? null : (
          <Field label={t("bookings.reschedule.newTime")} error={errors.time && t(errors.time)} required>
            {(control) => (
              <Input {...control} type="time" step={300} value={time} onChange={(event) => setTime(event.target.value)} />
            )}
          </Field>
        )}
      </div>
      {isStay ? null : (
        <SlotPicker
          request={{
            date,
            partySize: booking.party_size,
            resourceId: booking.resource_id,
            time: time || null,
            nights: null,
            isStay: false,
          }}
          selected={{ time: time || null, resourceId: booking.resource_id }}
          onPick={(slot) => {
            setTime(slot.time ?? time);
            setErrors({});
          }}
        />
      )}
      <CustomerLanguageSelect value={language} onChange={setLanguage} />
      <div className="flex flex-wrap justify-end gap-3 border-t border-line pt-4">
        <Button variant="secondary" onClick={onCancel} disabled={reschedule.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={reschedule.isPending} loadingText={t("bookings.reschedule.submitting")}>
          {t("bookings.reschedule.submit")}
        </Button>
      </div>
    </form>
  );
}
