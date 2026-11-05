"use client";

import type { ComponentProps } from "react";

import type { BookingUnit } from "@/components/insights/types";
import { Field, Input, TimeField } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import type { BookingFormErrors, BookingFormValues } from "../_lib/manualBooking";
import { SlotPicker } from "./SlotPicker";

/**
 * When: a time (and, for a service, its length) or nights for a stay, and
 * the free slots of the day to pick from (for the service's performers).
 */
export function BookingTimingFields({
  values,
  errors,
  unit,
  usualDuration,
  set,
  onPick,
}: {
  values: BookingFormValues;
  errors: BookingFormErrors;
  unit: BookingUnit;
  /** The chosen service's usual length in minutes. */
  usualDuration: number | null;
  set: <Key extends keyof BookingFormValues>(key: Key, value: BookingFormValues[Key]) => void;
  onPick: ComponentProps<typeof SlotPicker>["onPick"];
}) {
  const { t } = useI18n();
  const partySize = Number(values.partySize);
  const nights = Number(values.nights);
  const duration = Number(values.duration);
  const hasDuration = Boolean(values.serviceId) && unit !== "night";
  return (
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
              <TimeField {...control} value={values.time} step={15} onChange={(time) => set("time", time)} />
            )}
          </Field>
        )}
        {hasDuration ? (
          <Field
            label={t("bookings.form.duration")}
            hint={usualDuration ? t("bookings.form.durationHint", { count: usualDuration }) : undefined}
            error={errors.duration && t(errors.duration)}
          >
            {(control) => (
              <Input
                {...control}
                type="number"
                inputMode="numeric"
                min={5}
                max={43200}
                step={5}
                value={values.duration}
                onChange={(event) => set("duration", event.target.value)}
              />
            )}
          </Field>
        ) : null}
      </div>
      <SlotPicker
        request={{
          date: values.date,
          partySize: Number.isInteger(partySize) && partySize > 0 ? partySize : null,
          resourceId: values.resourceId || null,
          time: unit === "night" ? null : values.time || null,
          nights: unit === "night" && Number.isInteger(nights) && nights > 0 ? nights : null,
          isStay: unit === "night",
          serviceId: values.serviceId || null,
          durationMinutes: hasDuration && Number.isInteger(duration) && duration >= 5 ? duration : null,
        }}
        selected={{ time: values.time || null, resourceId: values.resourceId || null }}
        onPick={onPick}
      />
    </div>
  );
}
