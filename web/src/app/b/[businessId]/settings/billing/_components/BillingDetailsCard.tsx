"use client";

import { useMemo, useState } from "react";

import {
  Alert,
  Button,
  Card,
  ErrorState,
  Field,
  InlineError,
  Input,
  LoadingRegion,
  Select,
  SkeletonText,
  Textarea,
  useToast,
} from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryFlag, countryName } from "@/lib/countries";

import {
  billingCountryCodes,
  billingDetailsErrors,
  billingDetailsForm,
  billingProfileBody,
  formatTaxRate,
  hasDetailsErrors,
  isSameBillingDetails,
  MAX_ADDRESS_LENGTH,
  MAX_LEGAL_NAME_LENGTH,
  MAX_TAX_ID_LENGTH,
  VAT_TEXTS,
  type BillingDetailsErrors,
  type BillingDetailsForm,
  type BillingProfileView,
} from "../_lib/billingDetails";
import { useBillingDetails, type BillingDetailsState } from "../_lib/useBillingDetails";

/** "Реквизиты для счетов": what invoices and receipts name the business with, and the VAT that follows. */
export function BillingDetailsCard() {
  const { t } = useI18n();
  const state = useBillingDetails();
  const { profile } = state;

  return (
    <Card id="billing-details" title={t("billing.details.title")} description={t("billing.details.description")}>
      {profile.error && !profile.data ? (
        <ErrorState error={profile.error} onRetry={profile.reload} className="py-4" />
      ) : !profile.data ? (
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={4} />
        </LoadingRegion>
      ) : (
        // A new form when the stored details change (saved here or elsewhere).
        <BillingDetailsForm key={profile.data.is_saved ? "saved" : "new"} stored={profile.data} state={state} />
      )}
    </Card>
  );
}

function BillingDetailsForm({ stored, state }: { stored: BillingProfileView; state: BillingDetailsState }) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const [form, setForm] = useState<BillingDetailsForm>(() => billingDetailsForm(stored));
  const [isChecked, setIsChecked] = useState(false);
  const { save, profile } = state;
  const errors: BillingDetailsErrors = isChecked ? billingDetailsErrors(form) : {};
  const errorText = (field: keyof BillingDetailsErrors) => {
    const key = errors[field];
    return key ? t(key) : undefined;
  };
  const update = (change: Partial<BillingDetailsForm>) => setForm((current) => ({ ...current, ...change }));
  const countries = useMemo(
    () => billingCountryCodes((code) => countryName(code, locale), stored.country_code, locale),
    [locale, stored.country_code],
  );
  const disabled = save.isPending;

  const submit = async () => {
    setIsChecked(true);
    if (hasDetailsErrors(billingDetailsErrors(form))) {
      return;
    }
    const result = await save.run(billingProfileBody(form));
    if (result.ok) {
      profile.setData(result.data);
      setForm(billingDetailsForm(result.data));
      setIsChecked(false);
      toast.success(t("billing.details.saved"));
    }
  };

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {!stored.is_saved ? (
        <Alert tone="info">
          <p>{t("billing.details.notSaved")}</p>
        </Alert>
      ) : null}
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label={t("billing.details.legalName")} hint={t("billing.details.legalNameHint")} error={errorText("legalName")} required>
          {(control) => (
            <Input
              {...control}
              value={form.legalName}
              maxLength={MAX_LEGAL_NAME_LENGTH}
              dir="auto"
              autoComplete="organization"
              disabled={disabled}
              onChange={(event) => update({ legalName: event.target.value })}
            />
          )}
        </Field>
        <Field
          label={t("billing.details.taxId")}
          hint={t("billing.details.taxIdHint")}
          error={errorText("taxId")}
          optionalLabel={t("common.optional")}
        >
          {(control) => (
            <Input
              {...control}
              value={form.taxId}
              maxLength={MAX_TAX_ID_LENGTH}
              dir="ltr"
              autoComplete="off"
              spellCheck={false}
              disabled={disabled}
              onChange={(event) => update({ taxId: event.target.value })}
            />
          )}
        </Field>
        <Field label={t("billing.details.country")} hint={t("billing.details.countryHint")} required>
          {(control) => (
            <Select
              {...control}
              value={form.countryCode}
              autoComplete="country"
              disabled={disabled}
              onChange={(event) => update({ countryCode: event.target.value })}
            >
              {countries.map((code) => (
                <option key={code} value={code}>
                  {`${countryFlag(code)} ${countryName(code, locale)}`}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <Field
          label={t("billing.details.billingEmail")}
          hint={t("billing.details.billingEmailHint")}
          error={errorText("billingEmail")}
          optionalLabel={t("common.optional")}
        >
          {(control) => (
            <Input
              {...control}
              type="email"
              inputMode="email"
              dir="ltr"
              autoComplete="email"
              spellCheck={false}
              value={form.billingEmail}
              disabled={disabled}
              onChange={(event) => update({ billingEmail: event.target.value })}
            />
          )}
        </Field>
        <Field
          className="sm:col-span-2"
          label={t("billing.details.address")}
          error={errorText("address")}
          optionalLabel={t("common.optional")}
        >
          {(control) => (
            <Textarea
              {...control}
              rows={3}
              value={form.address}
              maxLength={MAX_ADDRESS_LENGTH}
              dir="auto"
              autoComplete="street-address"
              disabled={disabled}
              onChange={(event) => update({ address: event.target.value })}
            />
          )}
        </Field>
      </div>
      <p className="text-sm text-ink-muted">
        <span className="font-medium text-ink">{t("billing.details.vatLabel")}</span>{" "}
        {t(VAT_TEXTS[stored.tax_treatment], { rate: formatTaxRate(stored.tax_rate_basis_points, locale) })}
      </p>
      <InlineError error={save.error} />
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={isSameBillingDetails(form, stored)}
          isLoading={save.isPending}
          loadingText={t("common.saving")}
        >
          {t("billing.details.save")}
        </Button>
      </div>
    </form>
  );
}
