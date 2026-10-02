"use client";

import { Checkbox, ErrorState, Field, Fieldset, Select, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

import type { CreateBusinessState } from "../_lib/useCreateBusiness";

/**
 * What the country brings: currency, time zone (a choice when the country
 * has several), the customer languages and the default one.
 */
export function CountryDefaults({ form }: { form: CreateBusinessState }) {
  const { t, locale } = useI18n();
  const { profile, countryDefaults, countryZones, options, languages, errors } = form;

  const languageLabel = (tag: string) =>
    options.find((option) => option.tag === tag)?.native_name ?? languageName(tag, locale);

  return (
    <section className="space-y-5 rounded-xl border border-line bg-surface-muted/40 p-4 sm:p-5" aria-busy={profile.isLoading}>
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
                <Select {...control} value={form.timezone} onChange={(event) => form.setTimezone(event.target.value)}>
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
                  onChange={(event) => form.toggleLanguage(option.tag, event.target.checked)}
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
                  value={form.defaultLanguage}
                  onChange={(event) => form.setDefaultLanguage(event.target.value)}
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
  );
}
