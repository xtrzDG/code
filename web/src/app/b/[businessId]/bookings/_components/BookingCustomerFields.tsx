"use client";

import { useCountries } from "@/api/catalog";
import { Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName, formatCallingCode } from "@/lib/countries";

import type { BookingFormErrors, BookingFormValues } from "../_lib/manualBooking";

/** The customer's name and phone; the phone is read in the chosen country. */
export function BookingCustomerFields({
  values,
  errors,
  set,
}: {
  values: BookingFormValues;
  errors: BookingFormErrors;
  set: <Key extends keyof BookingFormValues>(key: Key, value: BookingFormValues[Key]) => void;
}) {
  const { t, locale } = useI18n();
  const countries = useCountries();
  const country = countries.data?.countries.find((item) => item.country_code === values.country);
  const phoneHint = t("bookings.form.phoneHint", {
    country: [
      countryFlag(values.country),
      countryName(values.country, locale),
      country ? `(${formatCallingCode(country.calling_code)})` : null,
    ]
      .filter(Boolean)
      .join(" "),
  });

  return (
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
          <div className="flex gap-2">
            <Select
              aria-label={t("bookings.form.phoneCountry")}
              value={values.country}
              onChange={(event) => set("country", event.target.value)}
              className="w-28 shrink-0"
            >
              {(countries.data?.countries ?? []).length === 0 ? (
                <option value={values.country}>{countryFlag(values.country)}</option>
              ) : (
                (countries.data?.countries ?? []).map((item) => (
                  <option key={item.country_code} value={item.country_code}>
                    {`${countryFlag(item.country_code)} ${formatCallingCode(item.calling_code)} ${countryName(item.country_code, locale)}`}
                  </option>
                ))
              )}
            </Select>
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
          </div>
        )}
      </Field>
    </div>
  );
}
