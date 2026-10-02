"use client";

import type { useNiches } from "@/api/catalog";
import type { BusinessView, CurrentUserView } from "@/api/types";
import { CountrySelect } from "@/components/CountrySelect";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { Alert, Button, ErrorState, Field, Input, LoadingBlock, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { CountryDefaults } from "./_components/CountryDefaults";
import { CreatedSummary } from "./_components/CreatedSummary";
import { MAX_NAME_LENGTH, useCreateBusiness } from "./_lib/useCreateBusiness";

/**
 * A new business: name, niche, country and city; the country's defaults
 * (CountryDefaults) can be adjusted before saving. The interface language
 * can be switched right here, since a new account sees this form first.
 */
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
  const { t } = useI18n();
  const form = useCreateBusiness(me, onCreated);
  const { countries, errors } = form;
  const niche = niches.data?.niches.find((item) => item.key === form.nicheKey);

  if (form.created) {
    return <CreatedSummary business={form.created} profile={form.countryDefaults} onClose={onCancel} />;
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

  return (
    <form noValidate onSubmit={form.submit} className="space-y-6">
      <LanguageSwitcher className="justify-between rounded-lg border border-line bg-surface-muted/40 py-1.5 pr-1.5 pl-3" />

      <Field label={t("businesses.name")} required error={errors.name && t(errors.name)}>
        {(control) => (
          <Input
            {...control}
            value={form.name}
            maxLength={MAX_NAME_LENGTH}
            autoComplete="organization"
            placeholder={t("businesses.namePlaceholder")}
            onChange={(event) => form.setName(event.target.value)}
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
          <Select {...control} value={form.nicheKey} onChange={(event) => form.setNicheKey(event.target.value)}>
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
            <CountrySelect {...control} countries={form.countryList} value={form.countryCode} onValueChange={form.setCountry} />
          )}
        </Field>
        <Field label={t("businesses.city")} optionalLabel={t("common.optional")}>
          {(control) => (
            <Input
              {...control}
              value={form.city}
              autoComplete="address-level2"
              placeholder={t("businesses.cityPlaceholder")}
              onChange={(event) => form.setCity(event.target.value)}
            />
          )}
        </Field>
      </div>

      <CountryDefaults form={form} />

      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={form.isSubmitting} loadingText={t("businesses.submitting")}>
          {t("businesses.submit")}
        </Button>
      </div>
    </form>
  );
}
