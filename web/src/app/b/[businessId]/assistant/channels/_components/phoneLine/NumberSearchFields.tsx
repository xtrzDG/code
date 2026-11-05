"use client";

/**
 * Where to look for a number: the country (those where a number is taken
 * at once first, then those our team arranges), its kind and, optionally,
 * a city or area to look near.
 */

import type { FormEvent } from "react";

import type { CountryListItem } from "@/api/types";
import { Button, Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";

import { PHONE_NUMBER_TYPES, groupCountries, type PhoneNumberType } from "../../_lib/phoneLine";

export interface NumberSearchForm {
  countryCode: string;
  numberType: PhoneNumberType;
  city: string;
}

export function NumberSearchFields({
  form,
  onChange,
  countries,
  selfServeCountries,
  isSearching,
  onSearch,
}: {
  form: NumberSearchForm;
  onChange: (change: Partial<NumberSearchForm>) => void;
  countries: readonly CountryListItem[];
  selfServeCountries: readonly string[];
  isSearching: boolean;
  onSearch: () => void;
}) {
  const { t, locale } = useI18n();
  const groups = groupCountries(countries, selfServeCountries);
  const label = (country: CountryListItem) => `${countryFlag(country.country_code)} ${country.display_name}`;
  const knownCountry = countries.some((country) => country.country_code === form.countryCode);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSearch();
  };

  return (
    <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2" aria-label={t("phoneNumbers.dialog.title")}>
      <Field label={t("phoneNumbers.dialog.country")}>
        {(control) => (
          <Select {...control} value={form.countryCode} onChange={(event) => onChange({ countryCode: event.target.value })}>
            {knownCountry ? null : (
              // Until the catalog loads (or for a country it lacks): the name, never a bare code.
              <option value={form.countryCode}>{`${countryFlag(form.countryCode)} ${countryName(form.countryCode, locale)}`}</option>
            )}
            {groups.now.length > 0 ? (
              <optgroup label={t("phoneNumbers.dialog.countriesNow")}>
                {groups.now.map((country) => (
                  <option key={country.country_code} value={country.country_code}>
                    {label(country)}
                  </option>
                ))}
              </optgroup>
            ) : null}
            <optgroup label={t("phoneNumbers.dialog.countriesTeam")}>
              {groups.team.map((country) => (
                <option key={country.country_code} value={country.country_code}>
                  {label(country)}
                </option>
              ))}
            </optgroup>
          </Select>
        )}
      </Field>
      <Field label={t("phoneNumbers.dialog.type")}>
        {(control) => (
          <Select
            {...control}
            value={form.numberType}
            onChange={(event) => onChange({ numberType: event.target.value as PhoneNumberType })}
          >
            {PHONE_NUMBER_TYPES.map((kind) => (
              <option key={kind} value={kind}>
                {t(`phoneNumbers.typeOptions.${kind}`)}
              </option>
            ))}
          </Select>
        )}
      </Field>
      <Field label={t("phoneNumbers.dialog.city")} hint={t("phoneNumbers.dialog.cityHint")} className="sm:col-span-2">
        {(control) => (
          <Input
            {...control}
            value={form.city}
            maxLength={60}
            autoComplete="address-level2"
            onChange={(event) => onChange({ city: event.target.value })}
          />
        )}
      </Field>
      <div className="sm:col-span-2">
        <Button type="submit" isLoading={isSearching} loadingText={t("phoneNumbers.dialog.searching")} fullWidth>
          {t("phoneNumbers.dialog.search")}
        </Button>
      </div>
    </form>
  );
}
