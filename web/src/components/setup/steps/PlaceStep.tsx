"use client";

/**
 * Step 2, "Where are you?": the country (prefilled from the owner's phone;
 * fixed once the business exists), the city, the address (required for
 * businesses that take bookings: customers need to find them), the
 * customer languages and the time zone. Checked on Continue.
 */

import { useState } from "react";

import { CountrySelect } from "@/components/CountrySelect";
import { ErrorState, Field, Input, LoadingRegion, Select, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";

import { LanguageChoice } from "../fields/LanguageChoice";
import { StepScreen } from "../StepScreen";
import { forCountry, type PlaceForm, type PlaceValues } from "../usePlace";

type Problem = "country" | "languages" | "address";

export function PlaceStep({
  form,
  onChange,
  place,
  isCountryFixed,
  isAddressRequired,
  onSubmit,
  onBack,
  isBusy,
  busyLabel,
}: {
  form: PlaceForm;
  onChange: (form: PlaceForm) => void;
  place: PlaceValues;
  isCountryFixed: boolean;
  isAddressRequired: boolean;
  onSubmit: () => void;
  onBack: () => void;
  isBusy?: boolean;
  busyLabel?: string;
}) {
  const { t, locale } = useI18n();
  const [problems, setProblems] = useState<Partial<Record<Problem, boolean>>>({});
  const { countryCode, defaults, languages } = place;

  const submit = () => {
    const found: Partial<Record<Problem, boolean>> = {
      country: !countryCode,
      languages: languages.length === 0,
      address: isAddressRequired && form.address.trim() === "",
    };
    setProblems(found);
    if (!Object.values(found).some(Boolean) && defaults) {
      onSubmit();
    }
  };

  const toggleLanguage = (tag: string, checked: boolean) => {
    const next = checked ? [...languages, tag] : languages.filter((item) => item !== tag);
    onChange({ ...form, languagesByCountry: forCountry(form.languagesByCountry, countryCode, next) });
    setProblems((current) => ({ ...current, languages: false }));
  };

  return (
    <StepScreen
      step="place"
      title={t("tunnelBusiness.place.title")}
      text={t("tunnelBusiness.place.text")}
      actions={{ onContinue: submit, onBack, isBusy, busyLabel, canContinue: Boolean(defaults) }}
    >
      {place.countries.error && !place.countries.data ? (
        <ErrorState error={place.countries.error} onRetry={place.countries.reload} />
      ) : !place.countries.data ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={5} />
        </LoadingRegion>
      ) : (
        <div className="space-y-8">
          <div className="grid gap-6 sm:grid-cols-2">
            {isCountryFixed && countryCode ? (
              <div className="space-y-1.5">
                <p className="text-sm font-medium text-ink">{t("tunnelBusiness.place.country")}</p>
                <p className="flex h-11 items-center gap-2 rounded-lg border border-line bg-surface-muted/60 px-3 text-ink">
                  <span aria-hidden>{countryFlag(countryCode)}</span>
                  {countryName(countryCode, locale)}
                </p>
                <p className="text-xs text-ink-subtle">{t("tunnelBusiness.place.countryFixed")}</p>
              </div>
            ) : (
              <Field
                label={t("tunnelBusiness.place.country")}
                required
                error={problems.country ? t("tunnelBusiness.place.errors.country") : undefined}
                hint={defaults ? t("tunnelBusiness.place.countryHint", { currency: `${defaults.currency_display_name} (${defaults.profile.currency_code})` }) : undefined}
              >
                {(control) => (
                  <CountrySelect
                    {...control}
                    countries={place.countryList}
                    value={countryCode}
                    onValueChange={(code) => {
                      onChange({ ...form, countryCode: code });
                      setProblems((current) => ({ ...current, country: false }));
                    }}
                  />
                )}
              </Field>
            )}
            <Field label={t("tunnelBusiness.place.city")} optionalLabel={t("common.optional")}>
              {(control) => (
                <Input
                  {...control}
                  value={form.city}
                  maxLength={120}
                  autoComplete="address-level2"
                  placeholder={t("tunnelBusiness.place.cityPlaceholder")}
                  onChange={(event) => onChange({ ...form, city: event.target.value })}
                />
              )}
            </Field>
          </div>

          <Field
            label={t("tunnelBusiness.place.address")}
            required={isAddressRequired}
            optionalLabel={isAddressRequired ? undefined : t("tunnelBusiness.place.addressOptional")}
            hint={t("tunnelBusiness.place.addressHint")}
            error={problems.address ? t("tunnelBusiness.place.errors.address") : undefined}
          >
            {(control) => (
              <Input
                {...control}
                value={form.address}
                maxLength={300}
                autoComplete="street-address"
                placeholder={t("tunnelBusiness.place.addressPlaceholder")}
                onChange={(event) => {
                  onChange({ ...form, address: event.target.value });
                  setProblems((current) => ({ ...current, address: false }));
                }}
              />
            )}
          </Field>

          {!defaults ? (
            <LoadingRegion label={t("common.loading")}>
              <SkeletonText lines={2} />
            </LoadingRegion>
          ) : (
            <section className="space-y-6 rounded-2xl border border-line bg-surface/80 p-5 backdrop-blur-sm sm:p-6">
              <LanguageChoice
                options={place.options}
                languages={languages}
                defaultLanguage={place.defaultLanguage}
                onToggle={toggleLanguage}
                onDefault={(tag) => onChange({ ...form, defaultByCountry: forCountry(form.defaultByCountry, countryCode, tag) })}
                error={problems.languages ? t("tunnelBusiness.place.errors.languages") : undefined}
              />
              {place.zones.length > 1 ? (
                <Field label={t("tunnelBusiness.place.timezone")}>
                  {(control) => (
                    <Select
                      {...control}
                      value={place.timezone}
                      onChange={(event) => onChange({ ...form, zoneByCountry: forCountry(form.zoneByCountry, countryCode, event.target.value) })}
                    >
                      {place.zones.map((zone) => (
                        <option key={zone.name} value={zone.name}>
                          {zone.display_name}
                        </option>
                      ))}
                    </Select>
                  )}
                </Field>
              ) : null}
            </section>
          )}
        </div>
      )}
    </StepScreen>
  );
}
