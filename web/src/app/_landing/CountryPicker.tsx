"use client";

import Form from "next/form";
import { useEffect, useId, useState } from "react";

import { useCountries } from "@/api/catalog";
import { Button, Select } from "@/components/ui";
import { useIsClient } from "@/components/workspace/useIsClient";
import { useI18n } from "@/i18n/client";
import { countryChoices, type CountryChoice } from "@/lib/publicSite/countryChoices";
import { inSequence } from "@/lib/waits";

import { afterPageLoad, whenIdle } from "./heroWaits";

/**
 * Whose prices to show: a GET form to the page itself (?country=XX). With JavaScript it
 * navigates as soon as a country is picked and keeps the scroll position;
 * without, the "Show" button submits it. The page brings the countries with
 * prices of their own and the one shown (pricedCountryChoices); every other
 * country joins once the page has loaded and the browser is idle.
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
  const choices = useAllCountries() ?? countries;

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
        {choices.map((country) => (
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

/** Every country of the catalog, asked for once the page has loaded and the browser is idle (null until then). */
function useAllCountries(): CountryChoice[] | null {
  const [isWanted, setIsWanted] = useState(false);
  useEffect(() => inSequence([afterPageLoad, whenIdle], () => setIsWanted(true)), []);
  const countries = useCountries({ enabled: isWanted });
  return countries.data ? countryChoices(countries.data.countries) : null;
}
