"use client";

import type { CountryListItem } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { countryOptionLabel, isCountryAvailable } from "@/lib/countries";

import { Select, type SelectProps } from "./ui/controls";

/**
 * Native country picker: "🇬🇪 Georgia (+995)". Countries where sign-up is
 * not available are listed but disabled.
 */
export function CountrySelect({
  countries,
  value,
  onValueChange,
  placeholder,
  ...props
}: Omit<SelectProps, "value" | "onChange" | "children"> & {
  countries: readonly CountryListItem[];
  value: string | null;
  onValueChange: (countryCode: string) => void;
  placeholder?: string;
}) {
  const { t } = useI18n();
  return (
    <Select value={value ?? ""} onChange={(event) => onValueChange(event.target.value)} {...props}>
      {value === null ? (
        <option value="" disabled>
          {placeholder ?? t("common.select")}
        </option>
      ) : null}
      {countries.map((country) => (
        <option key={country.country_code} value={country.country_code} disabled={!isCountryAvailable(country)}>
          {countryOptionLabel(country, t("auth.countryUnavailable"))}
        </option>
      ))}
    </Select>
  );
}
