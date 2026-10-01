"use client";

import { useState, type FormEvent } from "react";
import { z } from "zod";

import type { useNiches } from "@/api/catalog";
import { useCountries, useCountryProfile } from "@/api/catalog";
import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import type { BusinessView, CountryProfileView, CurrentUserView, LanguageOption, NicheKey } from "@/api/types";
import { CountrySelect } from "@/components/CountrySelect";
import { IconCheck } from "@/components/icons";
import {
  Alert,
  Button,
  ButtonLink,
  Checkbox,
  ErrorState,
  Field,
  Fieldset,
  Input,
  LoadingBlock,
  Select,
  Spinner,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { countryName, guessCountryCode, isCountryAvailable, pickInitialTimezone } from "@/lib/countries";
import { capitalizeFirst, languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";
import { fieldErrors, messageKey } from "@/lib/validation";

const MAX_NAME_LENGTH = 120;

const CreateBusinessSchema = z.object({
  name: z.string().trim().min(1, messageKey("businesses.errors.nameRequired")).max(MAX_NAME_LENGTH),
  niche_key: z.string().min(1, messageKey("businesses.errors.nicheRequired")),
  country_code: z.string().min(2, messageKey("businesses.errors.countryRequired")),
  city: z.string().trim().max(120),
  languages: z.array(z.string()).min(1, messageKey("businesses.errors.languagesRequired")),
});

function languageOptions(profile: CountryProfileView | undefined): LanguageOption[] {
  if (!profile) {
    return [];
  }
  const seen = new Set<string>();
  return [...profile.default_customer_languages, ...profile.on_request_customer_languages]
    .filter((option) => {
      if (seen.has(option.tag)) {
        return false;
      }
      seen.add(option.tag);
      return true;
    })
    .map((option) => ({
      ...option,
      native_name: capitalizeFirst(option.native_name, option.tag),
      display_name: capitalizeFirst(option.display_name),
    }));
}

export function CreateBusinessForm({
  me,
  niches,
  onCreated,
  onCancel,
}: {
  me: CurrentUserView;
  niches: ReturnType<typeof useNiches>;
  onCreated: (business: BusinessView) => void;
  onCancel: () => void;
}) {
  const { t, locale } = useI18n();
  const countries = useCountries();

  const [name, setName] = useState("");
  const [nicheKey, setNicheKey] = useState("");
  const [chosenCountry, setChosenCountry] = useState<string | null>(null);
  const [city, setCity] = useState("");
  const [languagesByCountry, setLanguagesByCountry] = useState<Record<string, string[]>>({});
  const [defaultByCountry, setDefaultByCountry] = useState<Record<string, string>>({});
  const [zoneByCountry, setZoneByCountry] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Partial<Record<string, MessageKey>>>({});
  const [created, setCreated] = useState<BusinessView | null>(null);

  const countryList = countries.data?.countries ?? [];
  const availableCodes = countryList.filter(isCountryAvailable).map((country) => country.country_code);
  const userCountry = me.user.country_code && availableCodes.includes(me.user.country_code) ? me.user.country_code : null;
  const countryCode =
    chosenCountry ??
    userCountry ??
    (availableCodes.length > 0 && typeof navigator !== "undefined"
      ? guessCountryCode(navigator.languages ?? [navigator.language], availableCodes)
      : null);

  const profile = useCountryProfile(countryCode);
  const countryDefaults = profile.data && profile.data.profile.country_code === countryCode ? profile.data : undefined;
  const options = languageOptions(countryDefaults);
  const languages =
    (countryCode ? languagesByCountry[countryCode] : undefined) ??
    countryDefaults?.default_customer_languages.map((option) => option.tag) ??
    [];
  const chosenDefault = countryCode ? defaultByCountry[countryCode] : undefined;
  const defaultLanguage = chosenDefault && languages.includes(chosenDefault) ? chosenDefault : languages[0];
  const niche = niches.data?.niches.find((item) => item.key === nicheKey);
  const countryZones = countryDefaults?.timezones ?? [];
  const timezone =
    (countryCode ? zoneByCountry[countryCode] : undefined) ??
    (countryDefaults
      ? pickInitialTimezone(
          countryZones.map((zone) => zone.name),
          countryDefaults.default_timezone.name,
          typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : null,
        )
      : undefined);

  const create = useApiMutation(
    (body: {
      name: string;
      niche_key: NicheKey;
      country_code: string;
      city?: string;
      timezone?: string;
      languages: string[];
      default_language?: string;
    }) =>
      api.POST("/v1/businesses", { body }),
    { errorMessages: { access_denied: "businesses.errors.countryRestricted" } },
  );

  const toggleLanguage = (tag: string, checked: boolean) => {
    if (!countryCode) {
      return;
    }
    const next = checked ? [...languages, tag] : languages.filter((item) => item !== tag);
    setLanguagesByCountry((current) => ({ ...current, [countryCode]: next }));
    setErrors((current) => ({ ...current, languages: undefined }));
  };

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = CreateBusinessSchema.safeParse({
      name,
      niche_key: nicheKey,
      country_code: countryCode ?? "",
      city,
      languages,
    });
    const found = fieldErrors(parsed);
    setErrors(found);
    if (!parsed.success) {
      return;
    }
    const result = await create.run({
      name: parsed.data.name,
      niche_key: parsed.data.niche_key as NicheKey,
      country_code: parsed.data.country_code,
      ...(parsed.data.city ? { city: parsed.data.city } : {}),
      ...(timezone ? { timezone } : {}),
      languages: parsed.data.languages,
      ...(defaultLanguage ? { default_language: defaultLanguage } : {}),
    });
    if (result.ok) {
      setCreated(result.data);
      onCreated(result.data);
    }
  }

  if (created) {
    return <CreatedSummary business={created} profile={countryDefaults} onClose={onCancel} />;
  }

  if (niches.error && !niches.data) {
    return <ErrorState error={niches.error} onRetry={niches.reload} />;
  }
  if (countries.error && !countries.data) {
    return <ErrorState error={countries.error} onRetry={countries.reload} />;
  }
  if (!niches.data || !countries.data) {
    return <LoadingBlock label={t("common.loading")} />;
  }

  const languageLabel = (tag: string) =>
    options.find((option) => option.tag === tag)?.native_name ?? languageName(tag, locale);

  return (
    <form noValidate onSubmit={onSubmit} className="space-y-6">
      <Field label={t("businesses.name")} required error={errors.name && t(errors.name)}>
        {(control) => (
          <Input
            {...control}
            value={name}
            maxLength={MAX_NAME_LENGTH}
            autoComplete="organization"
            placeholder={t("businesses.namePlaceholder")}
            onChange={(event) => setName(event.target.value)}
          />
        )}
      </Field>

      <Field
        label={t("businesses.niche")}
        required
        error={errors.niche_key && t(errors.niche_key)}
        hint={niche ? niche.description : undefined}
      >
        {(control) => (
          <Select {...control} value={nicheKey} onChange={(event) => setNicheKey(event.target.value)}>
            <option value="" disabled>
              {t("common.select")}
            </option>
            {niches.data?.niches.map((item) => (
              <option key={item.key} value={item.key}>
                {item.name}
              </option>
            ))}
          </Select>
        )}
      </Field>
      {niche?.requires_legal_review ? <Alert tone="warning">{t("businesses.nicheLegalReview")}</Alert> : null}

      <div className="grid gap-6 sm:grid-cols-2">
        <Field label={t("businesses.country")} required error={errors.country_code && t(errors.country_code)}>
          {(control) => (
            <CountrySelect
              {...control}
              countries={countryList}
              value={countryCode}
              onValueChange={(value) => setChosenCountry(value)}
            />
          )}
        </Field>
        <Field label={t("businesses.city")} optionalLabel={t("common.optional")}>
          {(control) => (
            <Input
              {...control}
              value={city}
              autoComplete="address-level2"
              placeholder={t("businesses.cityPlaceholder")}
              onChange={(event) => setCity(event.target.value)}
            />
          )}
        </Field>
      </div>

      <section className="space-y-5 rounded-xl border border-line bg-surface-muted/50 p-4 sm:p-5" aria-busy={profile.isLoading}>
        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-ink">{t("businesses.countryDefaults")}</h3>
          <p className="text-sm text-ink-muted">{t("businesses.countryDefaultsHint")}</p>
        </div>
        {profile.error && !countryDefaults ? (
          <ErrorState error={profile.error} onRetry={profile.reload} className="py-4" />
        ) : !countryDefaults ? (
          <div className="flex items-center gap-2 text-sm text-ink-muted">
            <Spinner size="sm" />
            {t("common.loading")}
          </div>
        ) : (
          <>
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-ink-subtle">{t("businesses.currency")}</dt>
                <dd className="mt-0.5 font-medium text-ink">
                  {countryDefaults.currency_display_name} ({countryDefaults.profile.currency_code})
                </dd>
              </div>
              {countryZones.length > 1 ? null : (
                <div>
                  <dt className="text-ink-subtle">{t("businesses.timezone")}</dt>
                  <dd className="mt-0.5 font-medium text-ink">{countryDefaults.default_timezone.display_name}</dd>
                </div>
              )}
            </dl>

            {countryZones.length > 1 ? (
              // A country spanning several zones: the owner picks theirs
              // (opening hours, bookings and reminders are counted in it).
              <Field label={t("businesses.timezone")} hint={t("businesses.timezoneHint")}>
                {(control) => (
                  <Select
                    {...control}
                    value={timezone}
                    onChange={(event) => {
                      const value = event.target.value;
                      if (countryCode) {
                        setZoneByCountry((current) => ({ ...current, [countryCode]: value }));
                      }
                    }}
                  >
                    {countryZones.map((zone) => (
                      <option key={zone.name} value={zone.name}>
                        {zone.display_name}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            ) : null}

            <Fieldset
              legend={t("businesses.languages")}
              hint={t("businesses.languagesHint")}
              error={errors.languages && t(errors.languages)}
            >
              <div className="grid gap-2 sm:grid-cols-2">
                {options.map((option) => (
                  <Checkbox
                    key={option.tag}
                    id={`language-${option.tag}`}
                    checked={languages.includes(option.tag)}
                    onChange={(event) => toggleLanguage(option.tag, event.target.checked)}
                    label={<span lang={option.tag}>{option.native_name}</span>}
                    description={option.display_name !== option.native_name ? option.display_name : undefined}
                  />
                ))}
              </div>
            </Fieldset>

            {languages.length > 1 ? (
              <Field label={t("businesses.defaultLanguage")} hint={t("businesses.defaultLanguageHint")}>
                {(control) => (
                  <Select
                    {...control}
                    value={defaultLanguage}
                    onChange={(event) => {
                      const value = event.target.value;
                      if (countryCode) {
                        setDefaultByCountry((current) => ({ ...current, [countryCode]: value }));
                      }
                    }}
                  >
                    {languages.map((tag) => (
                      <option key={tag} value={tag}>
                        {languageLabel(tag)}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            ) : null}
          </>
        )}
      </section>

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={create.isPending} loadingText={t("businesses.submitting")}>
          {t("businesses.submit")}
        </Button>
      </div>
    </form>
  );
}

function CreatedSummary({
  business,
  profile,
  onClose,
}: {
  business: BusinessView;
  profile: CountryProfileView | undefined;
  onClose: () => void;
}) {
  const { t, locale } = useI18n();
  const timezone = profile?.timezones.find((option) => option.name === business.timezone)?.display_name ?? business.timezone;
  const currency =
    profile && profile.profile.currency_code === business.currency_code
      ? `${profile.currency_display_name} (${business.currency_code})`
      : business.currency_code;
  const languageLabel = (tag: string) =>
    languageOptions(profile).find((option) => option.tag === tag)?.native_name ?? languageName(tag, locale);

  return (
    <div className="space-y-6">
      <Alert tone="success" title={t("businesses.createdTitle")}>
        {t("businesses.createdDescription", { country: countryName(business.country_code, locale) })}
      </Alert>
      <dl className="grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-ink-subtle">{t("businesses.currency")}</dt>
          <dd className="mt-0.5 font-medium text-ink">{currency}</dd>
        </div>
        <div>
          <dt className="text-ink-subtle">{t("businesses.timezone")}</dt>
          <dd className="mt-0.5 font-medium text-ink">{timezone}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-ink-subtle">{t("businesses.languages")}</dt>
          <dd className="mt-1 flex flex-wrap gap-2">
            {business.languages.map((tag) => (
              <span
                key={tag}
                lang={tag}
                className="inline-flex items-center gap-1 rounded-full bg-surface-muted px-2.5 py-1 text-xs font-medium text-ink"
              >
                {tag === business.default_language ? <IconCheck className="size-3.5 text-accent" aria-hidden /> : null}
                {languageLabel(tag)}
              </span>
            ))}
          </dd>
        </div>
      </dl>
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onClose}>
          {t("common.close")}
        </Button>
        <ButtonLink href={businessPath(business.id, "onboarding")}>{t("businesses.continueToProfile")}</ButtonLink>
      </div>
    </div>
  );
}
