"use client";

import Form from "next/form";
import { useId } from "react";

import { Button, Select } from "@/components/ui";
import { useIsClient } from "@/components/workspace/useIsClient";
import { useI18n } from "@/i18n/client";
import type { CountryChoice } from "@/lib/publicSite/countryChoices";

/**
 * Whose prices to show: a GET form to the page itself (?country=XX). With JavaScript it
 * navigates as soon as a country is picked and keeps the scroll position;
 * without, the "Show" button submits it. The countries come ready-made from
 * the server (countryChoices).
 */
export function CountryPicker({
  countries,
  value,
  action,
}: {
  countries: readonly CountryChoice[];
  value: string | null;
  action: string;
}) {
  const { t } = useI18n();
  const isClient = useIsClient();
  const id = useId();

  return (
    <Form action={action} scroll={false} replace className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <label htmlFor={id} className="text-sm text-ink-muted">
        {t("landing.pricing.country")}
      </label>
      <Select
        // A new server value (after navigation) resets the uncontrolled select.
        key={value ?? ""}
        id={id}
        name="country"
        defaultValue={value ?? ""}
        className="w-64 max-w-full"
        onChange={(event) => event.currentTarget.form?.requestSubmit()}
      >
        {countries.map((country) => (
          <option key={country.code} value={country.code} disabled={!country.isAvailable}>
            {country.label}
          </option>
        ))}
      </Select>
      {isClient ? null : (
        <Button type="submit" variant="secondary" size="sm">
          {t("landing.pricing.show")}
        </Button>
      )}
    </Form>
  );
}
